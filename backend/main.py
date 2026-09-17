"""
AgriCopilot — FastAPI Backend
Main application entry point with all API endpoints.
"""

import sys
import os

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models.schemas import (
    AnalysisRequest, AnalysisResponse,
    ChatRequest, ChatResponse,
)
from data_sources.weather import fetch_weather
from data_sources.nasa_power import fetch_nasa_power
from data_sources.soil import fetch_soil, _calc_suitability
from data_sources.market import fetch_market
from agents.copilot import run_analysis, run_chat
from rag.ingestion import ingest_built_in_knowledge
from api.ml_routes import router as ml_router
from api.vision_routes import router as vision_router
from api.risk_dashboard_routes import router as risk_dashboard_router

# ──────────────────────────────────────────────
# Application lifecycle
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    print("=" * 60)
    print("  AgriCopilot - Agricultural AI Decision Intelligence")
    print("=" * 60)
    print(f"  LLM Model: {settings.LLM_MODEL}")
    print(f"  Ollama Host: {settings.OLLAMA_HOST}")
    print(f"  ChromaDB: {settings.CHROMA_PERSIST_DIR}")
    print("=" * 60)

    # Initialize RAG knowledge base
    try:
        ingest_built_in_knowledge()
    except Exception as e:
        print(f"[WARN] RAG init failed (non-critical): {e}")

    yield

    print("\nAgriCopilot shutting down.")


# ──────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────

app = FastAPI(
    title="AgriCopilot API",
    description="Agricultural AI Decision Intelligence System — multimodal reasoning across weather, soil, satellite, and market data.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register ML routes
app.include_router(ml_router)
app.include_router(vision_router)
app.include_router(risk_dashboard_router)

# ──────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """System health check."""
    ollama_status = "unknown"
    try:
        import ollama
        ollama.list()
        ollama_status = "connected"
    except Exception:
        ollama_status = "disconnected"

    return {
        "status": "healthy",
        "service": "AgriCopilot API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "ollama": ollama_status,
        "llm_model": settings.LLM_MODEL,
        "supported_crops": list(settings.SUPPORTED_CROPS.keys()),
    }


# ──────────────────────────────────────────────
# Full Analysis Endpoint
# ──────────────────────────────────────────────

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_field(request: AnalysisRequest):
    """
    Run a complete agricultural analysis for a field location.

    Combines weather, soil, satellite, market, and climate data with
    AI-powered reasoning to generate actionable recommendations.
    """
    try:
        result = await run_analysis(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# ──────────────────────────────────────────────
# Chat Endpoint
# ──────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_copilot(request: ChatRequest):
    """
    Conversational interface — ask agricultural questions with
    context-aware, data-driven answers.
    """
    try:
        result = await run_chat(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# ──────────────────────────────────────────────
# Individual Data Source Endpoints
# ──────────────────────────────────────────────

@app.get("/api/weather/{lat}/{lon}")
async def get_weather(lat: float, lon: float, crop: str = "rice"):
    """Fetch weather data for a location."""
    try:
        data = await fetch_weather(lat, lon, crop)
        return data.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/soil/{lat}/{lon}")
async def get_soil(lat: float, lon: float, crop: str = "rice", soil_type: str = None):
    """Fetch soil properties for a location."""
    try:
        data = await fetch_soil(lat, lon, crop, user_soil_type=soil_type)
        return data.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/{crop}/{country}")
async def get_market(crop: str, country: str = "India"):
    """Fetch market data for a crop and country."""
    try:
        data = await fetch_market(crop, country)
        return data.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nasa/{lat}/{lon}")
async def get_nasa_power(lat: float, lon: float):
    """Fetch NASA POWER agroclimatology data."""
    try:
        data = await fetch_nasa_power(lat, lon)
        return data.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/crops")
async def list_crops():
    """List all supported crops with their parameters."""
    return settings.SUPPORTED_CROPS


@app.get("/api/recommend-crops/{lat}/{lon}")
async def recommend_crops(lat: float, lon: float, soil_type: str = None):
    """Recommend the top 3 crops based on soil and weather suitability."""
    try:
        soil = await fetch_soil(lat, lon, "rice", user_soil_type=soil_type) # Fetch base soil
        weather = await fetch_weather(lat, lon, "rice") # Fetch base weather
        
        scored_crops = []
        for crop_id, profile in settings.SUPPORTED_CROPS.items():
            # Basic soil suitability (may be None if no numeric data)
            suitability = _calc_suitability(soil, profile)
            if suitability is None:
                suitability = 50  # Neutral score when we can't compute
            
            # Basic weather suitability (temp match)
            if weather and weather.temperature_current is not None:
                t = weather.temperature_current
                opt_lo, opt_hi = profile.get("optimal_temp_c", (20, 30))
                if opt_lo - 5 <= t <= opt_hi + 5:
                    suitability += 10 # Boost for good temp
                else:
                    suitability -= 10 # Penalty for bad temp
            
            scored_crops.append({
                "crop_id": crop_id,
                "name": profile["name"],
                "score": min(100, max(0, suitability))
            })
            
        # Sort by score descending
        scored_crops.sort(key=lambda x: x["score"], reverse=True)
        return {"recommendations": scored_crops[:3]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# Run with: uvicorn main:app --reload --port 8000
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
