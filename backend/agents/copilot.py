"""
AgriCopilot Agent Orchestrator
The main brain — collects data from all sources, runs reasoning through
the LLM, and produces structured recommendations with confidence scores.
"""

import json
import asyncio
from datetime import datetime
import httpx


from config import settings
from models.schemas import (
    AnalysisRequest, AnalysisResponse, ChatRequest, ChatResponse,
    Recommendation, RiskLevel,
)
from data_sources.weather import fetch_weather
from data_sources.nasa_power import fetch_nasa_power
from data_sources.soil import fetch_soil
from data_sources.market import fetch_market
from data_sources.costs import fetch_cultivation_cost
from data_sources.satellite import fetch_ndvi
from data_sources.yield_data import get_historical_yield
from data_sources.crop_calendar import get_crop_calendar
from analysis_engine import build_forecasts_and_decision
from agents.prompts import SYSTEM_PROMPT, format_analysis_prompt, format_chat_prompt
from agents.confidence import calculate_overall_confidence, get_data_quality_report
from rag.ingestion import query_knowledge
from data_sources.web_search import searcher, format_search_results_for_llm


async def run_analysis(request: AnalysisRequest) -> AnalysisResponse:
    """Collect live data and return only source-backed analysis outputs."""
    lat, lon = request.latitude, request.longitude
    crop, country = request.crop, request.country
    weather, nasa, soil, market, cost_estimate, satellite = await asyncio.gather(
        fetch_weather(lat, lon, crop), fetch_nasa_power(lat, lon),
        fetch_soil(lat, lon, crop), fetch_market(crop, country, request.manual_market_price),
        fetch_cultivation_cost(crop, request.field_size_ha),
        fetch_ndvi(lat, lon)
    )
    forecasts, decision, insights = build_forecasts_and_decision(lat, lon, crop, weather, soil, request.planting_date)
    rag_context = query_knowledge(f"{crop} farming recommendations {country}", n_results=3)
    
    historical_yield = get_historical_yield(crop, country)
    crop_calendar = get_crop_calendar(crop, country)
    
    # We will pass satellite to prompt formatting in a subsequent step if needed, but for now we just pass it to response
    prompt = format_analysis_prompt(
        lat=lat, lon=lon, crop=crop, country=country, 
        weather=weather, soil=soil, market=market, nasa=nasa, 
        satellite=satellite, historical_yield=historical_yield, crop_calendar=crop_calendar, 
        rag_context=rag_context
    )
    recommendations = await _call_llm_for_analysis(prompt)
    overall_confidence = calculate_overall_confidence(weather, soil, market, nasa)
    data_quality = get_data_quality_report(weather, soil, market, nasa)
    return AnalysisResponse(
        location={"latitude": lat, "longitude": lon, "crop": crop, "country": country, "data_quality": data_quality},
        weather=weather, soil=soil, market=market, nasa_power=nasa, cost_estimate=cost_estimate, satellite=satellite,
        forecasts=forecasts, decision=decision, insights=insights, recommendations=recommendations,
        overall_confidence=overall_confidence,
        summary=_build_summary(settings.SUPPORTED_CROPS.get(crop, {}).get("name", crop), country, weather, soil, satellite, market, overall_confidence),
        timestamp=datetime.now().isoformat(),
    )

async def run_chat(request: ChatRequest) -> ChatResponse:
    """
    Conversational copilot interface:
    1. Fetch current data context
    2. Retrieve relevant knowledge via RAG
    3. Search web for latest info
    4. Generate conversational response with all context
    """
    lat, lon = request.latitude, request.longitude
    crop, country = request.crop, request.country

    # Fetch data (in parallel)
    weather, soil, market = await asyncio.gather(
        fetch_weather(lat, lon, crop),
        fetch_soil(lat, lon, crop),
        fetch_market(crop, country),
    )

    # Skip intensive search/RAG for simple greetings
    is_greeting = request.message.strip().lower() in ["hi", "hello", "hey", "greetings"]

    # RAG - retrieve from knowledge base
    rag_context = ""
    if not is_greeting:
        rag_context = query_knowledge(request.message, n_results=2)

    # WEB SEARCH - get latest information
    web_search_context = ""
    if not is_greeting:
        try:
            # Determine search topic from user query
            query_lower = request.message.lower()
            
            if any(word in query_lower for word in ["disease", "pest", "infection", "blight", "blast", "spot"]):
                search_result = await searcher.search_disease(request.message, crop)
            elif any(word in query_lower for word in ["weather", "rain", "flood", "drought", "temperature", "wind"]):
                search_result = await searcher.search_weather_impact(crop, country)
            elif any(word in query_lower for word in ["price", "market", "cost", "sell", "buy"]):
                search_result = await searcher.search_market_price(crop, country)
            elif any(word in query_lower for word in ["fertilizer", "nitrogen", "phosphorus", "potassium", "npk"]):
                search_result = await searcher.search_fertilizer_guide(crop)
            else:
                # General search
                search_result = await searcher.search(f"{request.message} {crop} {country}", topic="agriculture")
            
            if search_result.get("status") == "success":
                web_search_context = await format_search_results_for_llm(search_result)
        
        except Exception as e:
            print(f"[Copilot] Web search error: {e}")
            web_search_context = f"Web search unavailable: {str(e)}"

    # Combine all context
    combined_context = ""
    if rag_context or web_search_context:
        combined_context = f"{rag_context}\n\n{web_search_context}"

    # Build chat prompt with all context
    prompt = format_chat_prompt(
        question=request.message,
        lat=lat, lon=lon, crop=crop, country=country,
        weather=weather, soil=soil,
        market=market, rag_context=combined_context,
        conversation_history=request.conversation_history,
    )

    # Call LLM with system prompt + context
    response_text = await _call_llm_chat(prompt)

    # Calculate confidence
    confidence = calculate_overall_confidence(weather, soil, market, None)

    sources = []
    if weather:
        sources.append(f"weather ({weather.source})")
    if soil:
        sources.append(f"soil ({soil.source})")
    if market:
        sources.append(f"market ({market.source})")
    if rag_context:
        sources.append("knowledge-base (RAG)")
    if web_search_context and "Web search unavailable" not in web_search_context:
        sources.append("live web search (Tavily)")

    return ChatResponse(
        response=response_text,
        data_summary={
            "temperature": f"{weather.temperature_current}°C" if weather and weather.temperature_current else "N/A",
            "crop_health": "N/A",
            "soil_fertility": f"{soil.fertility_score}/100" if soil and soil.fertility_score else "N/A",
        },
        confidence=confidence,
        sources_used=sources,
    )


async def _call_llm_for_analysis(prompt: str) -> list[Recommendation]:
    """Call Groq API (or Ollama fallback) and parse structured recommendations."""
    raw = None
    # 1. Try Groq Cloud if API key is provided
    if getattr(settings, "USE_GROQ_API", 1) == 1 and settings.GROQ_API_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": settings.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 4096,
                "response_format": {"type": "json_object"}
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    raw = data["choices"][0]["message"]["content"]
                    print("[Copilot] Successfully generated recommendations via Groq Cloud.")
        except Exception as e:
            print(f"[Copilot] Groq API error: {e}, falling back to local Ollama...")

    # 2. No API Key Fallback
    if raw is None:
        print("[Copilot] Groq API Key missing or request failed.")
        return []

    return _parse_recommendations(raw)


async def _call_llm_chat(prompt: str) -> str:
    """Call Groq API (or Ollama fallback) for conversational response."""
    # 1. Try Groq Cloud
    if getattr(settings, "USE_GROQ_API", 1) == 1 and settings.GROQ_API_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": settings.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.5,
                "max_tokens": 2048,
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[Copilot] Groq chat error: {e}, falling back to local Ollama...")

    # 2. No API Key Fallback
    return "The AI Copilot requires an API key to function. Please add your Groq API Key to the backend `.env` file."



def _parse_recommendations(raw: str) -> list[Recommendation]:
    """Parse LLM output into structured Recommendation objects."""
    try:
        # Try to extract JSON from the response
        # LLMs sometimes wrap JSON in markdown code blocks
        cleaned = raw.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        # Find JSON array
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        if start >= 0 and end > start:
            cleaned = cleaned[start:end]

        items = json.loads(cleaned)

        recommendations = []
        for item in items:
            try:
                rec = Recommendation(
                    category=item.get("category", "general"),
                    title=item.get("title", "Recommendation"),
                    description=item.get("description", ""),
                    confidence=min(max(float(item.get("confidence", 50)), 0), 100),
                    priority=item.get("priority", "moderate"),
                    reasoning=item.get("reasoning", ""),
                    data_sources_used=item.get("data_sources_used", []),
                )
                recommendations.append(rec)
            except Exception:
                continue

        return recommendations

    except (json.JSONDecodeError, Exception) as e:
        print(f"[Copilot] Parse error: {e}")
        return []


def _build_summary(
    crop_name: str, country: str, weather, soil, ndvi, market, confidence: float
) -> str:
    """Build a human-readable summary of the analysis."""
    parts = [f"Agricultural analysis for {crop_name} in {country}."]

    if weather and weather.temperature_current:
        parts.append(
            f"Current conditions: {weather.temperature_current}°C, "
            f"{weather.humidity}% humidity, drought risk: {weather.drought_risk.value}."
        )

    if ndvi and ndvi.health_status:
        parts.append(f"Crop health: {ndvi.health_status} (NDVI: {ndvi.current_ndvi}).")

    if soil and soil.fertility_score:
        parts.append(f"Soil fertility: {soil.fertility_score}/100 ({soil.soil_type}).")

    if market and market.current_price_usd_ton:
        parts.append(
            f"Market price: ${market.current_price_usd_ton}/ton, trend: {market.price_trend}."
        )

    parts.append(f"Overall confidence: {confidence}%.")

    return " ".join(parts)
