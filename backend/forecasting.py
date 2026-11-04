"""
Time-Series Forecasting Module for AgriCopilot

Implements lightweight, interpretable forecasters for:
- Crop yield (Trained XGBoost / Conformal Prediction + agronomic fallback)
- Water stress index (soil moisture + weather)
- Disease risk (temperature + humidity + historical)
- Fertilizer recommendations (soil + yield forecast)

All models output predictions with confidence intervals.
"""

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
import json
import numpy as np
from abc import ABC, abstractmethod

from data_pipeline import (
    LocationKey, WeatherRecord, SoilRecord, 
    MarketRecord, CropHistoricalRecord, AlignedDataFrame
)


@dataclass
class ForecastResult:
    """Single forecast output with uncertainty."""
    variable: str  # "yield", "water_stress", "disease_risk", "nitrogen_need"
    date: date
    point_estimate: float
    lower_ci: float  # 5th percentile
    upper_ci: float  # 95th percentile
    confidence: float  # [0, 1]
    model_name: str
    explanation: str = ""


class Forecaster(ABC):
    """Base class for all forecasters."""
    
    @abstractmethod
    def forecast(self, aligned_data: AlignedDataFrame, days_ahead: int = 30) -> List[ForecastResult]:
        """Generate forecast(s) for the next N days."""
        pass
    
    @abstractmethod
    def train(self, historical_data: List[AlignedDataFrame]) -> None:
        """Train the forecaster on historical data."""
        pass


class YieldForecaster(Forecaster):
    """Predicts crop yield using trained XGBoost ML model or empirical agronomic fallback."""
    
    def __init__(self, crop: str = "rice"):
        self.crop = crop
        self.trained = False
        self.historical_yields: List[float] = []
        self.historical_features: List[Dict] = []
        self.mean_yield: float | None = None
        self.std_yield: float | None = None
    
    def train(self, historical_data: List[AlignedDataFrame]) -> None:
        """Learn yield distribution from historical records."""
        for record in historical_data:
            if record.historical:
                for hist in record.historical:
                    if hist.crop == self.crop:
                        self.historical_yields.append(hist.yield_kg_ha)
                        self.historical_features.append({
                            "irrigated": hist.irrigated,
                            "n_kg_ha": hist.fertilizer_n_kg_ha or 0,
                            "disease": 1 if hist.disease_occurrence == "high" else 0,
                        })
        
        if self.historical_yields:
            self.mean_yield = float(np.mean(self.historical_yields))
            self.std_yield = float(np.std(self.historical_yields))
            self.trained = True
    
    def forecast(self, aligned_data: AlignedDataFrame, days_ahead: int = 30) -> List[ForecastResult]:
        """Forecast yield using trained XGBoost model if available, else empirical formula."""
        results = []
        if not aligned_data.weather or not aligned_data.soil:
            return results
        
        weather = aligned_data.weather
        soil = aligned_data.soil
        
        # 1. Try to use the trained ML model registry (XGBoost with Split Conformal Prediction)
        try:
            from ml.yield_pred.models import YieldModelRegistry
            registry = YieldModelRegistry()
            registry.load_all()
            if registry.models:
                feat_dict = {
                    "temperature": float(weather.temperature_c),
                    "rainfall": float(weather.precipitation_mm),
                    "humidity": float(weather.humidity_percent),
                    "soil_ph": float(soil.ph or 6.5),
                    "soil_moisture": 30.0,
                    "nitrogen": float(soil.nitrogen_ppm or 150.0),
                    "phosphorus": 40.0,
                    "potassium": 200.0,
                    "ndvi": 0.55,
                    "field_size_ha": 2.0,
                }
                ml_pred = registry.predict(feat_dict, model_name="xgboost", alpha=0.1)
                if "error" not in ml_pred:
                    yield_kg = ml_pred["point_estimate"] * 1000.0
                    ci_lower_kg = ml_pred["conformal_interval"]["lower"] * 1000.0
                    ci_upper_kg = ml_pred["conformal_interval"]["upper"] * 1000.0
                    top_feature = ml_pred["shap_explanation"]["top_features"][0]["feature"] if ml_pred.get("shap_explanation", {}).get("top_features") else "weather"
                    
                    results.append(ForecastResult(
                        variable="yield_kg_ha",
                        date=aligned_data.date + timedelta(days=days_ahead),
                        point_estimate=round(yield_kg, 1),
                        lower_ci=round(max(0, ci_lower_kg), 1),
                        upper_ci=round(ci_upper_kg, 1),
                        confidence=0.9,
                        model_name="XGBoost (Conformal 90% CI + SHAP)",
                        explanation=f"Trained ML model prediction. Key driver: {top_feature}. Conformal coverage guaranteed.",
                    ))
                    return results
        except Exception:
            pass

        # 2. Agronomic empirical fallback
        gdd = max(0, (weather.temperature_max_c + weather.temperature_min_c) / 2 - 10)
        drought_factor = 1.0 - min(0.3, weather.drought_stress_index)
        from config import settings
        optimal_ph = settings.SUPPORTED_CROPS.get(aligned_data.crop, {}).get("optimal_ph", (5.5, 7.5))
        ph_factor = 1.0 if soil.ph and optimal_ph[0] <= soil.ph <= optimal_ph[1] else 0.8
        irrigation_factor = 1.2 if getattr(aligned_data, 'irrigation_expected', False) else 1.0
        base_yield = self.mean_yield or 3500.0
        std_yield = self.std_yield or 500.0
        yield_estimate = base_yield * drought_factor * ph_factor * irrigation_factor * (1 + gdd / 100)

        results.append(ForecastResult(
            variable="yield_kg_ha",
            date=aligned_data.date + timedelta(days=days_ahead),
            point_estimate=round(yield_estimate, 1),
            lower_ci=round(max(0, yield_estimate - 2 * std_yield), 1),
            upper_ci=round(yield_estimate + 2 * std_yield, 1),
            confidence=0.7 if self.trained else 0.5,
            model_name="YieldForecaster (Empirical)",
            explanation=f"Yield forecast for {aligned_data.crop}: Base={base_yield:.0f} kg/ha",
        ))
        return results


class WaterStressForecaster(Forecaster):
    """Predicts soil moisture and irrigation need."""
    
    def __init__(self):
        self.trained = False
        self.daily_et_mm = 3.0
    
    def train(self, historical_data: List[AlignedDataFrame]) -> None:
        self.trained = True
    
    def forecast(self, aligned_data: AlignedDataFrame, days_ahead: int = 30) -> List[ForecastResult]:
        results = []
        if not aligned_data.weather or not aligned_data.soil:
            return results
        
        weather = aligned_data.weather
        soil = aligned_data.soil
        awc = soil.available_water_capacity()
        soil_moisture_index = awc * 0.5
        
        pet_mm = 0.0023 * (weather.temperature_mean_c() + 17.8) * \
                 (weather.temperature_max_c - weather.temperature_min_c) ** 0.5 * \
                 max(1, weather.solar_radiation_mj_m2 / 24 if weather.solar_radiation_mj_m2 else 1)
        
        eta_mm = pet_mm * min(1.0, soil_moisture_index / awc * 2) if awc > 0 else pet_mm
        water_input_mm = weather.precipitation_mm
        drainage_mm = max(0, (awc - soil_moisture_index) * 0.1)
        net_change = water_input_mm - eta_mm - drainage_mm
        new_soil_moisture = min(awc, max(0, soil_moisture_index + net_change / 10))
        stress_index = 1.0 - (new_soil_moisture / awc) if awc > 0 else 0.5
        
        explanation = (
            f"Water balance: Rainfall={weather.precipitation_mm:.1f}mm, "
            f"PET={pet_mm:.1f}mm, "
            f"Drainage={drainage_mm:.1f}mm → "
            f"Soil moisture={new_soil_moisture:.1f}/{awc:.1f}mm, "
            f"Stress={stress_index:.2f} (0=dry, 1=wet)"
        )
        
        results.append(ForecastResult(
            variable="water_stress_index",
            date=aligned_data.date + timedelta(days=days_ahead),
            point_estimate=stress_index,
            lower_ci=max(0, stress_index - 0.15),
            upper_ci=min(1, stress_index + 0.15),
            confidence=0.6 if self.trained else 0.4,
            model_name="WaterStressForecaster",
            explanation=explanation,
        ))
        return results


class DiseaseRiskForecaster(Forecaster):
    """Predicts disease risk based on weather + historical patterns."""
    
    def __init__(self):
        self.trained = False
        self.high_risk_threshold = 0.7
    
    def train(self, historical_data: List[AlignedDataFrame]) -> None:
        self.trained = True
    
    def forecast(self, aligned_data: AlignedDataFrame, days_ahead: int = 30) -> List[ForecastResult]:
        results = []
        if not aligned_data.weather:
            return results
        
        weather = aligned_data.weather
        temp_risk = 0.0
        if 20 <= weather.temperature_c <= 28:
            temp_risk = 0.8
        elif 18 <= weather.temperature_c <= 30:
            temp_risk = 0.5
        
        humidity_risk = weather.humidity_percent / 100 * 0.7
        rainfall_risk = min(0.6, weather.precipitation_mm / 50)
        
        historical_risk = 0.0
        if aligned_data.historical:
            for hist in aligned_data.historical:
                if hist.disease_occurrence == "high":
                    historical_risk = 0.5
                    break
        
        disease_risk = (
            0.4 * temp_risk +
            0.35 * humidity_risk +
            0.15 * rainfall_risk +
            0.1 * historical_risk
        )
        
        risk_level = "high" if disease_risk > self.high_risk_threshold else \
                    "moderate" if disease_risk > 0.5 else "low"
        
        explanation = (
            f"Disease risk: Temp={weather.temperature_c:.1f}°C (risk={temp_risk:.2f}), "
            f"Humidity={weather.humidity_percent:.0f}% (risk={humidity_risk:.2f}), "
            f"Recent rain={weather.precipitation_mm:.1f}mm (risk={rainfall_risk:.2f}), "
            f"Overall={disease_risk:.2f} ({risk_level})"
        )
        
        results.append(ForecastResult(
            variable="disease_risk",
            date=aligned_data.date + timedelta(days=days_ahead),
            point_estimate=disease_risk,
            lower_ci=max(0, disease_risk - 0.2),
            upper_ci=min(1, disease_risk + 0.2),
            confidence=0.65 if self.trained else 0.45,
            model_name="DiseaseRiskForecaster",
            explanation=explanation,
        ))
        return results


class FertilizerRecommender(Forecaster):
    """Recommends fertilizer based on soil + yield forecast."""
    
    def __init__(self):
        self.trained = False
        self.crop_params = {
            "rice": {"n_uptake_kg_kg": 0.02, "p_uptake_kg_kg": 0.004, "k_uptake_kg_kg": 0.008},
            "maize": {"n_uptake_kg_kg": 0.025, "p_uptake_kg_kg": 0.005, "k_uptake_kg_kg": 0.006},
        }
    
    def train(self, historical_data: List[AlignedDataFrame]) -> None:
        self.trained = True
    
    def forecast(self, aligned_data: AlignedDataFrame, days_ahead: int = 30) -> List[ForecastResult]:
        results = []
        if not self.trained or not aligned_data.soil:
            return results
        
        soil = aligned_data.soil
        crop = aligned_data.crop
        params = self.crop_params.get(crop, {"n_uptake_kg_kg": 0.02, "p_uptake_kg_kg": 0.004})
        
        matching_history = [record.yield_kg_ha for record in aligned_data.historical if record.crop == crop]
        target_yield_kg_ha = sum(matching_history) / len(matching_history) if matching_history else 3500.0

        n_need_kg_ha = target_yield_kg_ha * params["n_uptake_kg_kg"]
        available_n_kg_ha = (soil.nitrogen_ppm or 20) * 2.5 / 100
        rec_n_kg_ha = max(0, n_need_kg_ha - available_n_kg_ha + 20)
        
        explanation = (
            f"Fertilizer for {crop}: "
            f"Target yield={target_yield_kg_ha:.0f} kg/ha, "
            f"N need={n_need_kg_ha:.0f} kg/ha, "
            f"Available soil N={available_n_kg_ha:.0f} kg/ha → "
            f"Recommend {rec_n_kg_ha:.0f} kg N/ha"
        )
        
        results.append(ForecastResult(
            variable="nitrogen_recommendation_kg_ha",
            date=aligned_data.date + timedelta(days=days_ahead),
            point_estimate=rec_n_kg_ha,
            lower_ci=max(0, rec_n_kg_ha - 50),
            upper_ci=rec_n_kg_ha + 50,
            confidence=0.5 if self.trained else 0.3,
            model_name="FertilizerRecommender",
            explanation=explanation,
        ))
        return results


class ForecastingPipeline:
    """Orchestrates all forecasters."""
    
    def __init__(self, crop: str = "rice"):
        self.crop = crop
        self.forecasters = {
            "yield": YieldForecaster(crop),
            "water_stress": WaterStressForecaster(),
            "disease_risk": DiseaseRiskForecaster(),
            "fertilizer": FertilizerRecommender(),
        }
    
    def train_all(self, historical_data: List[AlignedDataFrame]) -> None:
        """Train all forecasters."""
        for name, forecaster in self.forecasters.items():
            forecaster.train(historical_data)
    
    def forecast_all(self, aligned_data: AlignedDataFrame, days_ahead: int = 30) -> Dict[str, List[ForecastResult]]:
        """Run all forecasters and return results."""
        all_results = {}
        for name, forecaster in self.forecasters.items():
            try:
                results = forecaster.forecast(aligned_data, days_ahead)
                all_results[name] = results
            except Exception as e:
                all_results[name] = [ForecastResult(
                    variable=name,
                    date=aligned_data.date + timedelta(days=days_ahead),
                    point_estimate=0,
                    lower_ci=0,
                    upper_ci=0,
                    confidence=0,
                    model_name=forecaster.__class__.__name__,
                    explanation=f"Forecast failed: {str(e)}",
                )]
        return all_results
