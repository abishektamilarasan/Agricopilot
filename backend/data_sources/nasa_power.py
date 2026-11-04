"""
NASA POWER Agroclimatology Integration
Free API — no key required. Provides solar radiation, temperature,
humidity, and precipitation data optimized for agricultural modeling.
"""

import httpx
from datetime import datetime, timedelta
from models.schemas import NASAPowerData
from config import settings


async def fetch_nasa_power(lat: float, lon: float) -> NASAPowerData:
    """
    Fetch agroclimatology data from NASA POWER.

    Parameters retrieved (AG community):
    - ALLSKY_SFC_SW_DWN: Solar radiation (kWh/m²/day)
    - T2M: Temperature at 2m (°C)
    - RH2M: Relative humidity at 2m (%)
    - WS2M: Wind speed at 2m (m/s)
    - PRECTOTCORR: Corrected precipitation (mm/day)
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    params = {
        "parameters": "ALLSKY_SFC_SW_DWN,T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,PRECTOTCORR",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "format": "JSON",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(settings.NASA_POWER_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        properties = data.get("properties", {}).get("parameter", {})

        # Calculate averages from the last 30 days
        solar = _recent_avg(properties.get("ALLSKY_SFC_SW_DWN", {}), 30)
        temp = _recent_avg(properties.get("T2M", {}), 30)
        humidity = _recent_avg(properties.get("RH2M", {}), 30)
        wind = _recent_avg(properties.get("WS2M", {}), 30)
        precip = _recent_avg(properties.get("PRECTOTCORR", {}), 30)

        # Build monthly climatology (average each month over the year)
        monthly = _build_monthly_climatology(properties)

        return NASAPowerData(
            solar_radiation_kwh_m2=round(solar, 2) if solar else None,
            temperature_avg_c=round(temp, 1) if temp else None,
            relative_humidity_pct=round(humidity, 1) if humidity else None,
            wind_speed_m_s=round(wind, 1) if wind else None,
            precipitation_mm=round(precip, 1) if precip else None,
            monthly_climatology=monthly,
            source="nasa-power",
        )

    except Exception as e:
        print(f"[NASA POWER] Error fetching data: {e}")
        return NASAPowerData(source="unavailable")


def _recent_avg(param_dict: dict, days: int) -> float | None:
    """Average the most recent N days of data, skipping fill values (-999)."""
    if not param_dict:
        return None
    values = list(param_dict.values())[-days:]
    valid = [v for v in values if v is not None and v > -900]
    return sum(valid) / len(valid) if valid else None


def _build_monthly_climatology(properties: dict) -> list[dict]:
    """Aggregate daily data into monthly averages."""
    months = {}
    temp_data = properties.get("T2M", {})
    precip_data = properties.get("PRECTOTCORR", {})
    solar_data = properties.get("ALLSKY_SFC_SW_DWN", {})

    for date_str, temp in temp_data.items():
        if temp is None or temp < -900:
            continue
        month = date_str[4:6]
        if month not in months:
            months[month] = {"temps": [], "precips": [], "solars": []}
        months[month]["temps"].append(temp)

        precip = precip_data.get(date_str)
        if precip is not None and precip > -900:
            months[month]["precips"].append(precip)

        solar = solar_data.get(date_str)
        if solar is not None and solar > -900:
            months[month]["solars"].append(solar)

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]

    result = []
    for i, name in enumerate(month_names, 1):
        key = f"{i:02d}"
        if key in months:
            m = months[key]
            result.append({
                "month": name,
                "avg_temp_c": round(sum(m["temps"]) / len(m["temps"]), 1),
                "total_precip_mm": round(sum(m["precips"]), 1),
                "avg_solar_kwh": round(
                    sum(m["solars"]) / len(m["solars"]), 2
                ) if m["solars"] else None,
            })

    return result
