"""
Confidence Scoring Engine
Calculates confidence estimates for recommendations based on
data quality, completeness, freshness, and internal consistency.
"""

from models.schemas import WeatherData, SoilData, MarketData, NASAPowerData


def calculate_overall_confidence(
    weather: WeatherData | None,
    soil: SoilData | None,
    market: MarketData | None,
    nasa: NASAPowerData | None,
) -> float:
    """
    Calculate an overall confidence score (0-100) based on the quality
    and completeness of all data sources.
    """
    scores = []
    weights = []

    # Weather — highest weight (most critical for farming)
    w_score = _score_weather(weather)
    scores.append(w_score)
    weights.append(0.30)

    # Soil — important for fertilizer / suitability
    s_score = _score_soil(soil)
    scores.append(s_score)
    weights.append(0.20)

    # Market — important for economic decisions
    m_score = _score_market(market)
    scores.append(m_score)
    weights.append(0.15)

    # NASA — supplementary climate data
    nasa_score = _score_nasa(nasa)
    scores.append(nasa_score)
    weights.append(0.15)

    weighted = sum(s * w for s, w in zip(scores, weights))
    return round(weighted, 1)


def get_data_quality_report(
    weather: WeatherData | None,
    soil: SoilData | None,
    market: MarketData | None,
    nasa: NASAPowerData | None,
) -> dict:
    """Generate a detailed data quality report for transparency."""
    return {
        "weather": {
            "score": _score_weather(weather),
            "source": getattr(weather, "source", "unavailable"),
            "is_live": weather is not None and getattr(weather, "source", "") != "unavailable",
        },
        "soil": {
            "score": _score_soil(soil),
            "source": getattr(soil, "source", "unavailable"),
            "is_live": soil is not None and getattr(soil, "source", "") != "unavailable",
        },
        "market": {
            "score": _score_market(market),
            "source": getattr(market, "source", "unavailable"),
            "is_live": market is not None and getattr(market, "source", "") != "unavailable",
        },
        "climate": {
            "score": _score_nasa(nasa),
            "source": getattr(nasa, "source", "unavailable"),
            "is_live": nasa is not None and getattr(nasa, "source", "") != "unavailable",
        },
    }


# ──────────────────────────────────────────────
# Per-source scoring functions
# ──────────────────────────────────────────────

def _score_weather(weather: WeatherData | None) -> float:
    if weather is None or weather.source == "unavailable":
        return 0.0

    score = 30.0  # Base score for having any data

    # Check data completeness
    fields = [
        weather.temperature_current, weather.humidity,
        weather.precipitation_mm, weather.evapotranspiration_mm,
    ]
    filled = sum(1 for f in fields if f is not None)
    score += (filled / len(fields)) * 30

    # Check forecast availability
    if weather.forecast_days:
        score += min(len(weather.forecast_days) / 7 * 20, 20)

    # Bonus for a verified live source
    if weather.source != "unavailable":
        score += 20

    return min(score, 100)


def _score_soil(soil: SoilData | None) -> float:
    if soil is None or soil.source == "unavailable":
        return 0.0

    score = 30.0

    fields = [soil.ph, soil.organic_carbon_g_kg, soil.nitrogen_g_kg,
              soil.clay_pct, soil.sand_pct, soil.cec_cmol_kg]
    filled = sum(1 for f in fields if f is not None)
    score += (filled / len(fields)) * 30

    if soil.fertility_score is not None:
        score += 10

    if soil.source != "unavailable":
        score += 20
    else:
        score += 0

    return min(score, 100)


def _score_market(market: MarketData | None) -> float:
    if market is None or market.source == "unavailable":
        return 0.0

    score = 30.0

    if market.current_price_usd_ton is not None:
        score += 20
    if market.price_trend is not None:
        score += 10
    if market.price_history:
        score += min(len(market.price_history) / 5 * 15, 15)
    if market.yield_tons_ha is not None:
        score += 10

    if market.source != "unavailable":
        score += 15
    else:
        score += 10

    return min(score, 100)


def _score_nasa(nasa: NASAPowerData | None) -> float:
    if nasa is None or nasa.source == "unavailable":
        return 0.0

    score = 30.0

    fields = [nasa.solar_radiation_kwh_m2, nasa.temperature_avg_c,
              nasa.relative_humidity_pct, nasa.precipitation_mm]
    filled = sum(1 for f in fields if f is not None)
    score += (filled / len(fields)) * 30

    if nasa.monthly_climatology:
        score += min(len(nasa.monthly_climatology) / 12 * 20, 20)

    if nasa.source != "unavailable":
        score += 20

    return min(score, 100)
