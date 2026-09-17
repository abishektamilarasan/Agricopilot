"""Transforms live environmental data into transparent agricultural indicators."""

from datetime import date, datetime
from data_pipeline import AlignedDataFrame, DataSource, LocationKey, SoilRecord, WeatherRecord
from forecasting import ForecastingPipeline
from decision_fusion import DecisionFusionEngine
from models.schemas import SoilData, WeatherData


def build_forecasts_and_decision(lat: float, lon: float, crop: str, weather: WeatherData, soil: SoilData, planting_date: str | None) -> tuple[dict, dict | None, dict]:
    location = LocationKey(lat, lon)
    today = date.today()
    weather_record = _weather_record(location, today, weather)
    soil_record = _soil_record(location, soil)
    frame = AlignedDataFrame(location=location, date=today, crop=crop, weather=weather_record, soil=soil_record)
    frame.data_completeness = sum(item is not None for item in (weather_record, soil_record)) / 2

    pipeline = ForecastingPipeline(crop)
    raw = pipeline.forecast_all(frame)
    forecasts = {name: _serialize(results[0]) if results else None for name, results in raw.items()}
    forecasts["water_stress"] = _water_balance(weather)

    try:
        planted = datetime.strptime(planting_date, "%Y-%m-%d").date() if planting_date else today
    except ValueError:
        planted = today
    decision = _serialize_decision(DecisionFusionEngine(pipeline).fuse_and_decide(frame, planted))
    decision["irrigation"] = _irrigation_guidance(weather)
    return forecasts, decision, _insights(soil, weather, crop)


def _weather_record(location, today, weather):
    required = (weather.temperature_current, weather.temperature_min, weather.temperature_max, weather.humidity, weather.precipitation_mm, weather.wind_speed_kmh)
    if any(value is None for value in required):
        return None
    return WeatherRecord(location=location, date=today, source=DataSource.WEATHER, temperature_c=weather.temperature_current, temperature_min_c=weather.temperature_min, temperature_max_c=weather.temperature_max, humidity_percent=weather.humidity, precipitation_mm=weather.precipitation_mm, wind_speed_kmh=weather.wind_speed_kmh, drought_stress_index={"low": 0.0, "moderate": 0.4, "high": 0.7, "critical": 1.0}.get(weather.drought_risk.value, 0.0))


def _soil_record(location, soil):
    required = (soil.clay_pct, soil.sand_pct, soil.silt_pct, soil.ph, soil.organic_carbon_g_kg, soil.cec_cmol_kg)
    if any(value is None for value in required):
        return None
    return SoilRecord(location=location, source=DataSource.SOIL, clay_percent=soil.clay_pct, sand_percent=soil.sand_pct, silt_percent=soil.silt_pct, ph=soil.ph, organic_matter_percent=soil.organic_carbon_g_kg / 10, cation_exchange_capacity=soil.cec_cmol_kg, nitrogen_ppm=soil.nitrogen_g_kg * 1000 if soil.nitrogen_g_kg is not None else None)


def _water_balance(weather):
    if weather.precipitation_mm is None or weather.evapotranspiration_mm is None:
        return None
    deficit = round(max(weather.evapotranspiration_mm - weather.precipitation_mm, 0), 1)
    return {"variable": "seven_day_water_deficit_mm", "date": date.today().isoformat(), "point_estimate": deficit, "lower_ci": deficit, "upper_ci": deficit, "confidence": 0.7, "model_name": "Forecast rainfall minus FAO ET0", "explanation": f"Seven-day rainfall is {weather.precipitation_mm:.1f} mm and forecast ET0 is {weather.evapotranspiration_mm:.1f} mm. This is a weather balance, not a soil-sensor reading."}


def _irrigation_guidance(weather):
    balance = _water_balance(weather)
    if not balance:
        return None
    deficit = balance["point_estimate"]
    action = "Monitor field moisture; rainfall currently covers forecast evapotranspiration." if deficit == 0 else "Inspect field moisture before irrigating; this is the forecast water deficit, not a prescribed irrigation volume."
    return {"total_mm": deficit, "reasoning": f"{action} Deficit: {deficit:.1f} mm over the forecast period.", "confidence": "moderate"}


def _insights(soil, weather, crop):
    findings = []
    if soil.ph is not None:
        status = "acidic" if soil.ph < 5.5 else "alkaline" if soil.ph > 7.5 else "within the broad crop-friendly range"
        findings.append({"label": "Soil reaction (pH)", "value": soil.ph, "interpretation": f"{status}. Confirm lime/gypsum decisions with a laboratory soil test."})
    if soil.organic_carbon_g_kg is not None:
        status = "low" if soil.organic_carbon_g_kg < 5 else "moderate" if soil.organic_carbon_g_kg < 10 else "higher"
        findings.append({"label": "Organic carbon", "value": f"{soil.organic_carbon_g_kg} g/kg", "interpretation": f"Estimated {status}; retain residues and use organic amendments according to a local nutrient plan."})
    if soil.nitrogen_g_kg is not None:
        findings.append({"label": "Total nitrogen", "value": f"{soil.nitrogen_g_kg} g/kg", "interpretation": "SoilGrids estimate only. Do not convert this directly into fertilizer quantity; lab N, P and K testing is required."})
    if soil.soil_type:
        retention = "lower water holding and faster nutrient leaching" if soil.sand_pct and soil.sand_pct >= 60 else "higher water holding and drainage risk" if soil.clay_pct and soil.clay_pct >= 40 else "balanced drainage and water holding"
        findings.append({"label": "Texture", "value": soil.soil_type, "interpretation": f"Likely {retention}."})
    if soil.cec_cmol_kg is not None:
        findings.append({"label": "CEC", "value": f"{soil.cec_cmol_kg} cmol/kg", "interpretation": "Indicates the soil's estimated nutrient-holding capacity; interpret together with a local soil test."})
    limitations = ["SoilGrids is a 250 m global prediction surface, not an on-farm sample.", "Yield, fertilizer dosage and harvest profit require crop stage, field history, and laboratory N-P-K results."]
    return {"crop": crop, "findings": findings, "limitations": limitations, "weather_note": "Weather balances use forecast rainfall and FAO ET0; verify soil moisture in the field before applying water."}


def _serialize(result):
    return {"variable": result.variable, "date": result.date.isoformat(), "point_estimate": round(result.point_estimate, 2), "lower_ci": round(result.lower_ci, 2), "upper_ci": round(result.upper_ci, 2), "confidence": round(result.confidence, 2), "model_name": result.model_name, "explanation": result.explanation}


def _serialize_decision(decision):
    return {"irrigation": {"total_mm": decision.irrigation.total_mm, "reasoning": decision.irrigation.reasoning, "confidence": decision.irrigation.confidence.value} if decision.irrigation else None, "fertilizer": {"n_kg_ha": decision.fertilizer.n_kg_ha, "p_kg_ha": decision.fertilizer.p_kg_ha, "k_kg_ha": decision.fertilizer.k_kg_ha, "reasoning": decision.fertilizer.reasoning, "confidence": decision.fertilizer.confidence.value} if decision.fertilizer else None, "disease": {"risks": decision.disease_management.high_risk_diseases, "monitoring_frequency_days": decision.disease_management.monitoring_frequency_days, "reasoning": decision.disease_management.reasoning, "confidence": decision.disease_management.confidence.value} if decision.disease_management else None, "harvest": {"date": decision.harvest.estimated_harvest_date.isoformat(), "yield_kg_ha": decision.harvest.expected_yield_kg_ha, "profit_inr_per_ha": decision.harvest.expected_profit_per_ha, "reasoning": decision.harvest.reasoning, "confidence": decision.harvest.confidence.value} if decision.harvest else None, "limitations": decision.limitations}
