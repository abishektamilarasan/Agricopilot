"""Live SoilGrids integration for coordinate-based soil properties."""

import httpx
from config import settings
from models.schemas import SoilData
from data_sources.tn_soil_map import estimate_soil_type, get_soil_type_properties

_PROPERTIES = ["clay", "sand", "silt", "phh2o", "soc", "nitrogen", "cec"]


async def fetch_soil(lat: float, lon: float, crop: str = "rice", user_soil_type: str | None = None) -> SoilData:
    params = [("lon", lon), ("lat", lat), ("depth", "0-5cm"), ("value", "mean")]
    params.extend(("property", property_name) for property_name in _PROPERTIES)
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(settings.SOILGRIDS_URL, params=params)
            response.raise_for_status()
        values = _layer_values(response.json())
        clay = _convert(values.get("clay"), 10)
        sand = _convert(values.get("sand"), 10)
        silt = _convert(values.get("silt"), 10)
        soil = SoilData(
            clay_pct=clay, sand_pct=sand, silt_pct=silt,
            ph=_convert(values.get("phh2o"), 10),
            organic_carbon_g_kg=_convert(values.get("soc"), 10),
            nitrogen_g_kg=_convert(values.get("nitrogen"), 100),
            cec_cmol_kg=_convert(values.get("cec"), 10),
            soil_type=_texture_name(clay, sand, silt), source="SoilGrids 2.0",
        )
        soil.fertility_score = _calc_fertility(soil)
        soil.suitability_score = _calc_suitability(soil, settings.SUPPORTED_CROPS.get(crop, {}))
        return soil
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        # print(f"[SoilGrids] Error fetching soil data: {error}")
        return _fallback_soil(lat, lon, user_soil_type)


def _layer_values(payload: dict) -> dict[str, float | None]:
    values = {}
    for layer in payload.get("properties", {}).get("layers", []):
        depth = next((item for item in layer.get("depths", []) if item.get("label") == "0-5cm"), None)
        if depth:
            values[layer.get("name")] = depth.get("values", {}).get("mean")
    return values


def _convert(value: float | None, divisor: float) -> float | None:
    return round(float(value) / divisor, 2) if value is not None else None


def _texture_name(clay: float | None, sand: float | None, silt: float | None) -> str | None:
    if None in (clay, sand, silt):
        return None
    if clay >= 40:
        return "Clay"
    if sand >= 70:
        return "Sandy"
    if silt >= 50:
        return "Silty"
    return "Loam"


def _calc_fertility(soil: SoilData) -> float | None:
    if any(value is None for value in (soil.organic_carbon_g_kg, soil.nitrogen_g_kg, soil.cec_cmol_kg)):
        return None
    return round(min(100, 50 + min(20, soil.organic_carbon_g_kg / 30 * 20) + min(15, soil.nitrogen_g_kg / 2 * 15) + min(15, soil.cec_cmol_kg / 30 * 15)), 1)


def _calc_suitability(soil: SoilData, crop_profile: dict) -> float | None:
    if any(value is None for value in (soil.ph, soil.clay_pct, soil.sand_pct)):
        return None
    low, high = crop_profile.get("optimal_ph", (6.0, 7.0))
    ph_score = 25 if low <= soil.ph <= high else max(0, 25 - min(abs(soil.ph - low), abs(soil.ph - high)) * 10)
    texture_score = 15 if 15 <= soil.clay_pct <= 35 and 25 <= soil.sand_pct <= 50 else 5
    return round(min(100, 50 + ph_score + texture_score), 1)


def _fallback_soil(lat: float, lon: float, user_soil_type: str | None = None) -> SoilData:
    """
    Fallback when SoilGrids API fails.
    Uses the TN soil map for soil TYPE only.
    All numeric properties (pH, N, CEC, etc.) remain None — we never fabricate.
    If user provided a soil_type override, use that instead.
    """
    # If user explicitly provided a soil type, use it
    if user_soil_type and user_soil_type.strip():
        props = get_soil_type_properties(user_soil_type.strip())
        if props:
            return SoilData(
                soil_type=user_soil_type.strip(),
                description=props.get("description", ""),
                pros=f"Typical crops: {props.get('major_crops', 'N/A')}",
                cons=props.get("constraints", ""),
                source=f"User-provided ({user_soil_type.strip()})",
            )
        # User typed a custom name we don't recognize — still use it
        return SoilData(
            soil_type=user_soil_type.strip(),
            source=f"User-provided ({user_soil_type.strip()})",
        )

    # Try TN soil map estimation
    estimate = estimate_soil_type(lat, lon)
    if estimate:
        soil_type_name = estimate["soil_type"]
        return SoilData(
            soil_type=soil_type_name,
            description=estimate.get("description", ""),
            pros=f"Typical crops: {estimate.get('major_crops', 'N/A')}. pH range: {estimate.get('ph_range', 'N/A')}",
            cons=estimate.get("constraints", ""),
            source=f"TN Soil Survey (estimated) — {estimate.get('estimation_method', 'NBSSLUP')}",
        )

    # Outside TN or no match
    return SoilData(source="unavailable")
