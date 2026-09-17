"""
AgriCopilot Data Schemas
Pydantic models for all request/response payloads and internal data structures.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ──────────────────────────────────────────────
# Request Models
# ──────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    """Request for a full agricultural analysis."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude of the field")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude of the field")
    crop: str = Field(default="rice", description="Crop type to analyze")
    country: str = Field(default="India", description="Country for market data")
    planting_date: Optional[str] = Field(None, description="Planting date (YYYY-MM-DD)")
    field_size_ha: Optional[float] = Field(None, description="Field size in hectares")
    manual_market_price: Optional[float] = Field(None, description="Manually provided market price in INR/quintal")


class ChatRequest(BaseModel):
    """Request for the chat copilot interface."""
    message: str = Field(..., description="User message / question")
    latitude: float = Field(default=20.5937, ge=-90, le=90)
    longitude: float = Field(default=78.9629, ge=-180, le=180)
    crop: str = Field(default="rice")
    country: str = Field(default="India")
    soil_type: Optional[str] = Field(default=None, description="Soil type from location picker")
    conversation_history: list[dict] = Field(default_factory=list)


# ──────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────

class WeatherData(BaseModel):
    """Weather forecast and current conditions."""
    temperature_current: Optional[float] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    humidity: Optional[float] = None
    precipitation_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    evapotranspiration_mm: Optional[float] = None
    soil_moisture: Optional[float] = None
    forecast_days: list[dict] = Field(default_factory=list)
    growing_degree_days: Optional[float] = None
    heat_stress_days: int = 0
    drought_risk: RiskLevel = RiskLevel.LOW
    source: str = "open-meteo"


class SoilData(BaseModel):
    """Soil properties for a location."""
    ph: Optional[float] = None
    organic_carbon_g_kg: Optional[float] = None
    nitrogen_g_kg: Optional[float] = None
    clay_pct: Optional[float] = None
    sand_pct: Optional[float] = None
    silt_pct: Optional[float] = None
    cec_cmol_kg: Optional[float] = None
    soil_type: Optional[str] = None
    description: Optional[str] = None
    pros: Optional[str] = None
    cons: Optional[str] = None
    fertility_score: Optional[float] = None
    suitability_score: Optional[float] = None
    source: str = "soilgrids"


class MarketData(BaseModel):
    """Crop market and economic data."""
    crop: str = ""
    current_price_usd_ton: Optional[float] = None
    current_price_inr_quintal: Optional[float] = None
    price_trend: Optional[str] = None
    production_tons: Optional[float] = None
    yield_tons_ha: Optional[float] = None
    price_history: list[dict] = Field(default_factory=list)
    profitability_score: Optional[float] = None
    source: str = "faostat"


class NASAPowerData(BaseModel):
    """NASA POWER agroclimatology data."""
    solar_radiation_kwh_m2: Optional[float] = None
    temperature_avg_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    wind_speed_m_s: Optional[float] = None
    precipitation_mm: Optional[float] = None
    monthly_climatology: list[dict] = Field(default_factory=list)
    source: str = "nasa-power"


class SatelliteData(BaseModel):
    """Satellite imagery and NDVI data."""
    current_ndvi: Optional[float] = None
    health_status: Optional[str] = None
    image_url: Optional[str] = None
    cloud_coverage_pct: Optional[float] = None
    source: str = "agromonitoring"


class CostEstimate(BaseModel):
    """Source-attributed cultivation cost estimate."""
    crop: str
    method: Optional[str] = None
    cost_inr_per_ha: Optional[float] = None
    field_size_ha: Optional[float] = None
    total_cost_inr: Optional[float] = None
    source: str = "unavailable"
    source_url: Optional[str] = None
    note: Optional[str] = None


# ──────────────────────────────────────────────
# Recommendation Models
# ──────────────────────────────────────────────

class Recommendation(BaseModel):
    """A single actionable recommendation."""
    category: str = Field(..., description="yield|irrigation|fertilizer|disease|harvest|market")
    title: str = Field(..., description="Short recommendation title")
    description: str = Field(..., description="Detailed recommendation")
    confidence: float = Field(..., ge=0, le=100, description="Confidence percentage")
    priority: RiskLevel = RiskLevel.MODERATE
    reasoning: str = Field(default="", description="Explanation of why this recommendation was made")
    data_sources_used: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    """Full analysis response combining all data and recommendations."""
    location: dict = Field(default_factory=dict)
    weather: Optional[WeatherData] = None
    soil: Optional[SoilData] = None
    market: Optional[MarketData] = None
    nasa_power: Optional[NASAPowerData] = None
    satellite: Optional[SatelliteData] = None
    cost_estimate: Optional[CostEstimate] = None
    forecasts: dict = Field(default_factory=dict)
    decision: Optional[dict] = None
    insights: dict = Field(default_factory=dict)
    recommendations: list[Recommendation] = Field(default_factory=list)
    overall_confidence: float = 0.0
    summary: str = ""
    timestamp: str = ""


class ChatResponse(BaseModel):
    """Response from the chat copilot."""
    response: str = ""
    recommendations: list[Recommendation] = Field(default_factory=list)
    data_summary: Optional[dict] = None
    confidence: float = 0.0
    sources_used: list[str] = Field(default_factory=list)
