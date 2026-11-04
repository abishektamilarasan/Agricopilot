"""
Risk Dashboard API Routes
─────────────────────────
Exposes the Explainable AI Risk Dashboard via a POST endpoint.
Fetches live data from all sources, runs Dempster-Shafer evidence
fusion, and returns a fully transparent risk heatmap with
chain-of-thought audit trails.
"""

import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.schemas import AnalysisRequest
from data_sources.weather import fetch_weather
from data_sources.nasa_power import fetch_nasa_power
from data_sources.soil import fetch_soil
from data_sources.market import fetch_market
from data_sources.satellite import fetch_ndvi
from agents.explainability import generate_risk_dashboard

router = APIRouter(prefix="/api", tags=["Explainable AI Risk Dashboard"])


class RiskDashboardRequest(BaseModel):
    """Request body for the risk dashboard — same fields as AnalysisRequest."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude of the field")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude of the field")
    crop: str = Field(default="rice", description="Crop type to analyze")
    country: str = Field(default="India", description="Country for market data")


@router.post("/risk-dashboard")
async def risk_dashboard(request: RiskDashboardRequest):
    """
    Explainable AI Risk Dashboard (Novelty Feature)
    ─────────────────────────────────────────────────
    Returns a 6-dimension risk heatmap with:
      • Dempster-Shafer evidence fusion scores
      • Belief / Plausibility intervals for each risk
      • Step-by-step chain-of-thought reasoning
      • Composite Field Health Score (0-100, A-F grade)

    This endpoint fetches live data from all integrated sources
    (weather, soil, satellite, market, NASA) and fuses them using
    Dempster-Shafer Theory — a mathematically principled approach
    to combining uncertain evidence from heterogeneous sensors.
    """
    try:
        lat, lon = request.latitude, request.longitude
        crop, country = request.crop, request.country

        # Fetch all data sources in parallel
        weather, nasa, soil, market, satellite = await asyncio.gather(
            fetch_weather(lat, lon, crop),
            fetch_nasa_power(lat, lon),
            fetch_soil(lat, lon, crop),
            fetch_market(crop, country),
            fetch_ndvi(lat, lon),
        )

        # Run Dempster-Shafer fusion
        result = generate_risk_dashboard(
            crop=crop,
            weather=weather,
            soil=soil,
            market=market,
            nasa=nasa,
            satellite=satellite,
        )

        return result.to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk dashboard failed: {str(e)}")
