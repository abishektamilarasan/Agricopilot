"""
Open-Meteo Weather Integration
Free weather API — no key required. Provides forecast, historical, and
agricultural-specific variables (evapotranspiration, soil moisture).
"""

import httpx
from datetime import datetime, timedelta
from models.schemas import WeatherData, RiskLevel
from config import settings


async def fetch_weather(lat: float, lon: float, crop: str = "rice") -> WeatherData:
    """
    Fetch comprehensive weather data for agricultural analysis.

    Includes: temperature, precipitation, humidity, wind, ET₀, soil moisture,
    plus derived metrics (GDD, heat stress, drought risk).
    """
    crop_profile = settings.SUPPORTED_CROPS.get(crop, settings.SUPPORTED_CROPS["rice"])

    # --- Current + 7-day forecast ---
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m",
            "soil_moisture_0_to_1cm",
        ],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "precipitation_sum",
            "et0_fao_evapotranspiration",
            "wind_speed_10m_max",
            "relative_humidity_2m_mean",
        ],
        "forecast_days": 7,
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(settings.OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        current = data.get("current", {})
        daily = data.get("daily", {})

        # Build forecast day list
        forecast_days = []
        dates = daily.get("time", [])
        for i, date in enumerate(dates):
            forecast_days.append({
                "date": date,
                "temp_max": _safe_idx(daily.get("temperature_2m_max"), i),
                "temp_min": _safe_idx(daily.get("temperature_2m_min"), i),
                "temp_mean": _safe_idx(daily.get("temperature_2m_mean"), i),
                "precipitation_mm": _safe_idx(daily.get("precipitation_sum"), i),
                "et0_mm": _safe_idx(daily.get("et0_fao_evapotranspiration"), i),
                "wind_max_kmh": _safe_idx(daily.get("wind_speed_10m_max"), i),
                "humidity_pct": _safe_idx(daily.get("relative_humidity_2m_mean"), i),
            })

        # --- Derived agricultural metrics ---
        base_temp = crop_profile["base_temp_c"]
        gdd = _calc_gdd(daily, base_temp)
        heat_stress = _count_heat_stress_days(daily, crop_profile["optimal_temp_c"][1])
        precip_total = sum(
            p for p in (daily.get("precipitation_sum") or []) if p is not None
        )
        et0_total = sum(
            e for e in (daily.get("et0_fao_evapotranspiration") or []) if e is not None
        )
        drought_risk = _assess_drought_risk(precip_total, et0_total)

        temps_min = daily.get("temperature_2m_min", [])
        temps_max = daily.get("temperature_2m_max", [])

        return WeatherData(
            temperature_current=current.get("temperature_2m"),
            temperature_min=min((t for t in temps_min if t is not None), default=None),
            temperature_max=max((t for t in temps_max if t is not None), default=None),
            humidity=current.get("relative_humidity_2m"),
            precipitation_mm=precip_total,
            wind_speed_kmh=current.get("wind_speed_10m"),
            evapotranspiration_mm=et0_total,
            soil_moisture=current.get("soil_moisture_0_to_1cm"),
            forecast_days=forecast_days,
            growing_degree_days=gdd,
            heat_stress_days=heat_stress,
            drought_risk=drought_risk,
            source="open-meteo",
        )

    except Exception as e:
        print(f"[Weather] Error fetching data: {e}")
        return WeatherData(source="unavailable")


def _safe_idx(lst: list | None, idx: int):
    """Safely index into a list that might be None or short."""
    if lst is None or idx >= len(lst):
        return None
    return lst[idx]


def _calc_gdd(daily: dict, base_temp: float) -> float:
    """Calculate Growing Degree Days from daily mean temps."""
    means = daily.get("temperature_2m_mean", [])
    gdd = 0.0
    for t in means:
        if t is not None and t > base_temp:
            gdd += t - base_temp
    return round(gdd, 1)


def _count_heat_stress_days(daily: dict, max_optimal: float) -> int:
    """Count days exceeding optimal temperature threshold."""
    maxes = daily.get("temperature_2m_max", [])
    return sum(1 for t in maxes if t is not None and t > max_optimal + 3)


def _assess_drought_risk(precip_mm: float, et0_mm: float) -> RiskLevel:
    """Assess drought risk based on precipitation vs evapotranspiration."""
    if et0_mm <= 0:
        return RiskLevel.LOW
    ratio = precip_mm / et0_mm
    if ratio >= 0.8:
        return RiskLevel.LOW
    elif ratio >= 0.5:
        return RiskLevel.MODERATE
    elif ratio >= 0.3:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL
