"""
AgriCopilot Prompt Engineering
Expert-crafted system prompts and chain-of-thought templates for
multi-source agricultural reasoning.
"""

# ──────────────────────────────────────────────
# System Prompt — defines the copilot persona
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are AgriCopilot, an expert agricultural AI decision-support system specializing in Tamil Nadu, India.
You prioritize agricultural practices recommended by the Tamil Nadu Agricultural University (TNAU).
You combine data from multiple sources — weather forecasts, soil analysis, satellite vegetation
indices, market prices, and agricultural knowledge bases — to provide actionable farming
recommendations with confidence estimates tailored for Tamil Nadu farmers.

## Your capabilities:
- Yield prediction based on weather, soil, and crop growth models
- Water stress assessment and irrigation scheduling
- Disease and pest risk evaluation from environmental conditions
- Fertilizer recommendations based on soil nutrient analysis
- Harvest timing optimization
- Economic profitability analysis from market trends

## Your principles:
1. ALWAYS cite which data sources informed each recommendation
2. ALWAYS provide a confidence percentage (0-100%) for each recommendation
3. Explain your reasoning step-by-step
4. Flag when data is insufficient or uncertain
5. Prioritize recommendations by urgency (critical > high > moderate > low)
6. Use practical, farmer-friendly language
7. Consider local conditions and traditional practices
8. When uncertain, be honest about limitations

"""


# ──────────────────────────────────────────────
# Analysis Prompt Template
# ──────────────────────────────────────────────

ANALYSIS_PROMPT = """Analyze the following agricultural data and provide comprehensive
farming recommendations. Reason step-by-step across all data sources.

## Location
- Coordinates: {lat}°N, {lon}°E
- Crop: {crop}
- Country/Region: {country}

## Weather Data (Source: {weather_source})
- Current Temperature: {temp_current}°C
- Temperature Range: {temp_min}°C to {temp_max}°C
- Humidity: {humidity}%
- Precipitation (7-day total): {precipitation}mm
- Evapotranspiration (7-day): {et0}mm
- Soil Moisture: {soil_moisture}
- Growing Degree Days: {gdd}
- Heat Stress Days: {heat_stress_days}
- Drought Risk: {drought_risk}

## Soil Data (Source: {soil_source})
- pH: {soil_ph}
- Organic Carbon: {organic_carbon} g/kg
- Nitrogen: {nitrogen} g/kg
- Texture: Clay {clay}%, Sand {sand}%, Silt {silt}%
- CEC: {cec} cmol/kg
- Soil Type: {soil_type}
- Fertility Score: {fertility_score}/100
- Crop Suitability: {suitability_score}/100


## Market Data (Source: {market_source})
- Current Price: ${market_price}/ton
- Price Trend: {price_trend}
- Profitability Score: {profitability}/100

## Historical Yield Data (Source: {yield_source})
- Average Yield: {avg_yield} tons/ha
- Max Potential Yield: {max_yield} tons/ha
- Notes: {yield_notes}

## Crop Calendar Data (Source: {calendar_source})
{calendar_data}

## Solar & Climate Data (Source: {nasa_source})
- Solar Radiation: {solar_radiation} kWh/m²/day
- Average Temperature: {nasa_temp}°C
- Relative Humidity: {nasa_humidity}%

## Satellite Data (Source: {satellite_source})
- Current NDVI: {current_ndvi}
- Crop Health Status: {health_status}

{rag_context}

## Instructions
Based on ALL the above data sources, provide exactly 3-5 high-priority recommendations covering aspects like:
Yield Forecast, Irrigation, Fertilizer, Disease Risk, Harvest Timing, or Market Strategy.
Keep explanations extremely concise to save time.

For each recommendation, provide:
- A confidence percentage based on data quality and completeness
- Which specific data sources informed the recommendation
- Clear reasoning explaining WHY you made this recommendation

Format your response as a JSON array of objects with these fields:
"category", "title", "description", "confidence", "priority" (low/moderate/high/critical),
"reasoning", "data_sources_used" (array of strings)

Respond with ONLY the JSON array, no other text.
"""


# ──────────────────────────────────────────────
# Chat Prompt Template
# ──────────────────────────────────────────────

CHAT_PROMPT = """You are AgriCopilot, a helpful and knowledgeable agricultural AI assistant.
Answer the farmer's question using the provided data context.
Be natural, friendly, and practical. Keep your answers concise and conversational.
Do not use rigid formatting unless necessary for clarity.
Focus strictly on agriculture and farming-related topics.

## Current Agricultural Context
Location: {lat}AN, {lon}AE | Crop: {crop} | Country: {country}

Weather: {temp_current}AC, {humidity}% humidity, {precipitation}mm rain (7-day),
Drought Risk: {drought_risk}

Soil: pH {soil_ph}, Fertility: {fertility_score}/100, Type: {soil_type}

Market: ${market_price}/ton, Trend: {price_trend}

{rag_context}

## Conversation History
{conversation_history}

## Farmer's Question
{question}

## Instructions
- Answer naturally based on the data context above.
- If you cannot answer confidently, let the user know.
- Be concise but thorough.
"""


# ──────────────────────────────────────────────
# Helper to format data into prompts
# ──────────────────────────────────────────────

def format_analysis_prompt(
    lat: float,
    lon: float,
    crop: str,
    country: str,
    weather=None,
    soil=None,
    market=None,
    nasa=None,
    satellite=None,
    historical_yield=None,
    crop_calendar=None,
    rag_context: str = "",
) -> str:
    """Fill the analysis prompt template with actual data."""

    def _v(val, default="N/A"):
        return val if val is not None else default

    rag_section = ""
    if rag_context:
        rag_section = f"\n## Agricultural Knowledge Base Context\n{rag_context}\n"

    calendar_str = "N/A"
    calendar_src = "N/A"
    if crop_calendar and hasattr(crop_calendar, "seasons"):
        calendar_src = getattr(crop_calendar, "source", "N/A")
        seasons_info = []
        for s in crop_calendar.seasons:
            seasons_info.append(f"- {s.name}: Sowing ({', '.join(s.sowing_months)}), Harvest ({', '.join(s.harvesting_months)})")
        calendar_str = "\n".join(seasons_info)

    return ANALYSIS_PROMPT.format(
        lat=lat, lon=lon, crop=crop, country=country,
        # Weather
        weather_source=_v(getattr(weather, "source", None)),
        temp_current=_v(getattr(weather, "temperature_current", None)),
        temp_min=_v(getattr(weather, "temperature_min", None)),
        temp_max=_v(getattr(weather, "temperature_max", None)),
        humidity=_v(getattr(weather, "humidity", None)),
        precipitation=_v(getattr(weather, "precipitation_mm", None)),
        et0=_v(getattr(weather, "evapotranspiration_mm", None)),
        soil_moisture=_v(getattr(weather, "soil_moisture", None)),
        gdd=_v(getattr(weather, "growing_degree_days", None)),
        heat_stress_days=_v(getattr(weather, "heat_stress_days", None), 0),
        drought_risk=_v(getattr(weather, "drought_risk", None)),
        # Soil
        soil_source=_v(getattr(soil, "source", None)),
        soil_ph=_v(getattr(soil, "ph", None)),
        organic_carbon=_v(getattr(soil, "organic_carbon_g_kg", None)),
        nitrogen=_v(getattr(soil, "nitrogen_g_kg", None)),
        clay=_v(getattr(soil, "clay_pct", None)),
        sand=_v(getattr(soil, "sand_pct", None)),
        silt=_v(getattr(soil, "silt_pct", None)),
        cec=_v(getattr(soil, "cec_cmol_kg", None)),
        soil_type=_v(getattr(soil, "soil_type", None)),
        fertility_score=_v(getattr(soil, "fertility_score", None)),
        suitability_score=_v(getattr(soil, "suitability_score", None)),
        # Market
        market_source=_v(getattr(market, "source", None)),
        market_price=_v(getattr(market, "current_price_usd_ton", None)),
        price_trend=_v(getattr(market, "price_trend", None)),
        profitability=_v(getattr(market, "profitability_score", None)),
        # Yield
        yield_source=_v(getattr(historical_yield, "source", None)),
        avg_yield=_v(getattr(historical_yield, "average_yield_tons_ha", None)),
        max_yield=_v(getattr(historical_yield, "max_potential_yield_tons_ha", None)),
        yield_notes=_v(getattr(historical_yield, "notes", None)),
        # Calendar
        calendar_source=calendar_src,
        calendar_data=calendar_str,
        # NASA
        nasa_source=_v(getattr(nasa, "source", None)),
        solar_radiation=_v(getattr(nasa, "solar_radiation_kwh_m2", None)),
        nasa_temp=_v(getattr(nasa, "temperature_avg_c", None)),
        nasa_humidity=_v(getattr(nasa, "relative_humidity_pct", None)),
        # Satellite
        satellite_source=_v(getattr(satellite, "source", None)),
        current_ndvi=_v(getattr(satellite, "current_ndvi", None)),
        health_status=_v(getattr(satellite, "health_status", None)),
        # RAG
        rag_context=rag_section,
    )


def format_chat_prompt(
    question: str,
    lat: float,
    lon: float,
    crop: str,
    country: str,
    weather=None,
    soil=None,
    market=None,
    rag_context: str = "",
    conversation_history: list = None,
) -> str:
    """Fill the chat prompt template."""

    def _v(val, default="N/A"):
        return val if val is not None else default

    history_str = ""
    if conversation_history:
        for msg in conversation_history[-6:]:  # Last 6 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_str += f"{role.capitalize()}: {content}\n"

    rag_section = ""
    if rag_context:
        rag_section = f"\nRelevant Knowledge:\n{rag_context}\n"

    return CHAT_PROMPT.format(
        lat=lat, lon=lon, crop=crop, country=country,
        temp_current=_v(getattr(weather, "temperature_current", None)),
        humidity=_v(getattr(weather, "humidity", None)),
        precipitation=_v(getattr(weather, "precipitation_mm", None)),
        drought_risk=_v(getattr(weather, "drought_risk", None)),
        soil_ph=_v(getattr(soil, "ph", None)),
        fertility_score=_v(getattr(soil, "fertility_score", None)),
        soil_type=_v(getattr(soil, "soil_type", None)),
        market_price=_v(getattr(market, "current_price_usd_ton", None)),
        price_trend=_v(getattr(market, "price_trend", None)),
        rag_context=rag_section,
        conversation_history=history_str or "None",
        question=question,
    )
