"""
Data Schema & ETL Pipeline for AgriCopilot

Defines unified data structures and alignment logic for:
- Weather (daily forecasts & historical)
- Soil properties (static + dynamic)
- Market prices (time-series)
- Crop historical data (yields, practices)

All aligned to a common spatiotemporal key: (lat, lon, date).
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, Dict, List, Any
import hashlib
import json


class DataSource(str, Enum):
    """Enumeration of data sources."""
    WEATHER = "weather"
    SOIL = "soil"
    MARKET = "market"
    NASA_POWER = "nasa_power"
    HISTORICAL = "historical"
    USER = "user"


@dataclass
class LocationKey:
    """Unique identifier for a location."""
    latitude: float
    longitude: float
    
    def hash(self) -> str:
        """Generate consistent hash for caching."""
        loc_str = f"{self.latitude:.4f}_{self.longitude:.4f}"
        return hashlib.md5(loc_str.encode()).hexdigest()
    
    def __eq__(self, other):
        if not isinstance(other, LocationKey):
            return False
        return abs(self.latitude - other.latitude) < 0.01 and \
               abs(self.longitude - other.longitude) < 0.01
    
    def __hash__(self):
        return hash((round(self.latitude, 4), round(self.longitude, 4)))


@dataclass
class WeatherRecord:
    """Unified weather observation or forecast."""
    location: LocationKey
    date: date
    source: DataSource = field(default=DataSource.WEATHER, kw_only=True)
    
    # Core meteorological variables
    temperature_c: float  # Mean daily temperature
    temperature_min_c: float
    temperature_max_c: float
    humidity_percent: float  # Relative humidity
    precipitation_mm: float  # Daily rain/snow
    wind_speed_kmh: float
    solar_radiation_mj_m2: Optional[float] = None  # MJ/m²/day
    
    # Derived stress indicators
    heat_stress_days: float = 0.0  # GDD > 35°C
    cold_stress_days: float = 0.0  # GDD < 10°C
    drought_stress_index: float = 0.0  # 0-1, normalized
    
    # Metadata
    forecast: bool = False  # True if forecast, False if observed
    confidence: float = 1.0  # [0, 1] for forecasts
    ingested_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "lat": self.location.latitude,
            "lon": self.location.longitude,
            "date": self.date.isoformat(),
            "source": self.source.value,
            "temp_c": self.temperature_c,
            "temp_min_c": self.temperature_min_c,
            "temp_max_c": self.temperature_max_c,
            "humidity_pct": self.humidity_percent,
            "precip_mm": self.precipitation_mm,
            "wind_kmh": self.wind_speed_kmh,
            "solar_mj_m2": self.solar_radiation_mj_m2,
            "heat_stress": self.heat_stress_days,
            "cold_stress": self.cold_stress_days,
            "drought_stress_idx": self.drought_stress_index,
            "forecast": self.forecast,
            "confidence": self.confidence,
        }


@dataclass
class SoilRecord:
    """Soil properties at a location."""
    location: LocationKey
    source: DataSource = field(default=DataSource.SOIL, kw_only=True)
    
    # Soil composition (0-30cm layer)
    clay_percent: float
    sand_percent: float
    silt_percent: float
    ph: float  # Soil pH
    organic_matter_percent: float
    cation_exchange_capacity: float  # meq/100g
    
    # Nutrient content (mg/kg or ppm)
    nitrogen_ppm: Optional[float] = None
    phosphorus_ppm: Optional[float] = None
    potassium_ppm: Optional[float] = None
    micronutrients: Dict[str, float] = field(default_factory=dict)  # Fe, Zn, B, etc.
    
    # Water properties
    field_capacity_percent: float = 25.0  # Water retention
    wilting_point_percent: float = 10.0
    bulk_density_g_cm3: float = 1.3
    
    # Metadata
    depth_cm: int = 30  # Sampling depth
    survey_date: Optional[date] = None
    confidence: float = 0.8  # Spatial interpolation confidence
    ingested_at: datetime = field(default_factory=datetime.utcnow)
    
    def available_water_capacity(self) -> float:
        """Available water capacity: FC - WP."""
        return self.field_capacity_percent - self.wilting_point_percent
    
    def to_dict(self) -> Dict:
        return {
            "lat": self.location.latitude,
            "lon": self.location.longitude,
            "clay_pct": self.clay_percent,
            "sand_pct": self.sand_percent,
            "silt_pct": self.silt_percent,
            "ph": self.ph,
            "org_matter_pct": self.organic_matter_percent,
            "cec": self.cation_exchange_capacity,
            "n_ppm": self.nitrogen_ppm,
            "p_ppm": self.phosphorus_ppm,
            "k_ppm": self.potassium_ppm,
            "fc_pct": self.field_capacity_percent,
            "wp_pct": self.wilting_point_percent,
            "awc_pct": self.available_water_capacity(),
        }


@dataclass
class MarketRecord:
    """Commodity price observation."""
    location: LocationKey
    crop: str
    date: date
    source: DataSource = field(default=DataSource.MARKET, kw_only=True)
    
    price_per_kg: float  # Local currency
    volume_traded_tons: Optional[float] = None
    price_trend: Optional[str] = None  # "up", "down", "stable"
    
    # Derived features
    seasonal_avg_price: Optional[float] = None
    price_volatility: float = 0.0  # Standard deviation
    
    ingested_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "lat": self.location.latitude,
            "lon": self.location.longitude,
            "crop": self.crop,
            "date": self.date.isoformat(),
            "price_per_kg": self.price_per_kg,
            "volume_tons": self.volume_traded_tons,
            "trend": self.price_trend,
            "volatility": self.price_volatility,
        }


@dataclass
class CropHistoricalRecord:
    """Historical crop performance data."""
    location: LocationKey
    crop: str
    season_year: int
    source: DataSource = field(default=DataSource.HISTORICAL, kw_only=True)
    
    yield_kg_ha: float  # Actual yield achieved
    irrigated: bool
    fertilizer_n_kg_ha: Optional[float] = None
    fertilizer_p_kg_ha: Optional[float] = None
    fertilizer_k_kg_ha: Optional[float] = None
    
    disease_occurrence: Optional[str] = None  # "none", "low", "moderate", "high"
    pest_occurrence: Optional[str] = None
    water_stress_level: Optional[str] = None  # "none", "low", "moderate", "high"
    
    planting_date: Optional[date] = None
    harvest_date: Optional[date] = None
    notes: str = ""
    
    ingested_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "lat": self.location.latitude,
            "lon": self.location.longitude,
            "crop": self.crop,
            "year": self.season_year,
            "yield_kg_ha": self.yield_kg_ha,
            "irrigated": self.irrigated,
            "n_kg_ha": self.fertilizer_n_kg_ha,
            "p_kg_ha": self.fertilizer_p_kg_ha,
            "k_kg_ha": self.fertilizer_k_kg_ha,
            "disease": self.disease_occurrence,
            "pests": self.pest_occurrence,
            "water_stress": self.water_stress_level,
        }


@dataclass
class AlignedDataFrame:
    """Unified view of all data for a location-date range."""
    location: LocationKey
    date: date
    crop: str
    
    weather: Optional[WeatherRecord] = None
    soil: Optional[SoilRecord] = None
    market: Optional[MarketRecord] = None
    historical: List[CropHistoricalRecord] = field(default_factory=list)
    
    # Alignment metadata
    data_completeness: float = 0.0  # [0, 1] fraction of expected fields present
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "location": {"lat": self.location.latitude, "lon": self.location.longitude},
            "date": self.date.isoformat(),
            "crop": self.crop,
            "weather": self.weather.to_dict() if self.weather else None,
            "soil": self.soil.to_dict() if self.soil else None,
            "market": self.market.to_dict() if self.market else None,
            "historical_count": len(self.historical),
            "completeness": self.data_completeness,
        }
    
    def is_ready_for_prediction(self) -> bool:
        """Check if data is sufficient for predictions."""
        has_weather = self.weather is not None
        has_soil = self.soil is not None
        # Require weather + soil for minimal predictions
        return has_weather and has_soil


class ETLPipeline:
    """Orchestrates data ingestion, validation, and alignment."""
    
    def __init__(self):
        self.records: Dict[str, Dict] = {}  # Indexed by location_hash + date
        self.validation_log: List[str] = []
    
    def ingest_weather(self, record: WeatherRecord) -> bool:
        """Validate and ingest weather record."""
        try:
            # Basic validation
            assert -90 <= record.location.latitude <= 90
            assert -180 <= record.location.longitude <= 180
            assert -50 <= record.temperature_c <= 60
            assert 0 <= record.humidity_percent <= 100
            assert record.precipitation_mm >= 0
            
            key = self._make_key(record.location, record.date)
            if key not in self.records:
                self.records[key] = {}
            self.records[key]["weather"] = record
            return True
        except AssertionError as e:
            self.validation_log.append(f"Weather validation failed: {e}")
            return False
    
    def ingest_soil(self, record: SoilRecord) -> bool:
        """Validate and ingest soil record."""
        try:
            assert -90 <= record.location.latitude <= 90
            assert -180 <= record.location.longitude <= 180
            assert 0 <= record.clay_percent + record.sand_percent + record.silt_percent <= 105
            assert 3 <= record.ph <= 10
            
            key = self._make_key(record.location, date.today())
            if key not in self.records:
                self.records[key] = {}
            self.records[key]["soil"] = record
            return True
        except AssertionError as e:
            self.validation_log.append(f"Soil validation failed: {e}")
            return False
    
    def ingest_market(self, record: MarketRecord) -> bool:
        """Validate and ingest market record."""
        try:
            assert record.price_per_kg >= 0
            assert record.crop in ["rice", "maize", "millets", "cotton", "wheat"]
            
            key = self._make_key(record.location, record.date)
            if key not in self.records:
                self.records[key] = {}
            self.records[key]["market"] = record
            return True
        except AssertionError as e:
            self.validation_log.append(f"Market validation failed: {e}")
            return False
    
    def ingest_historical(self, record: CropHistoricalRecord) -> bool:
        """Validate and ingest historical crop data."""
        try:
            assert record.yield_kg_ha >= 0
            assert 2000 <= record.season_year <= 2100
            
            key = self._make_key(record.location, date(record.season_year, 1, 1))
            if key not in self.records:
                self.records[key] = {}
            if "historical" not in self.records[key]:
                self.records[key]["historical"] = []
            self.records[key]["historical"].append(record)
            return True
        except AssertionError as e:
            self.validation_log.append(f"Historical validation failed: {e}")
            return False
    
    def align_for_location_date(self, location: LocationKey, target_date: date, crop: str) -> AlignedDataFrame:
        """Fetch and align all data for a location and date."""
        key = self._make_key(location, target_date)
        data = self.records.get(key, {})
        
        frame = AlignedDataFrame(
            location=location,
            date=target_date,
            crop=crop,
            weather=data.get("weather"),
            soil=data.get("soil"),
            market=data.get("market"),
            historical=data.get("historical", []),
        )
        
        # Compute completeness
        completeness_count = sum([
            1 if frame.weather else 0,
            1 if frame.soil else 0,
            1 if frame.market else 0,
            1 if len(frame.historical) > 0 else 0,
        ])
        frame.data_completeness = completeness_count / 4.0
        
        return frame
    
    @staticmethod
    def _make_key(location: LocationKey, d: date) -> str:
        """Create unique composite key."""
        return f"{location.hash()}_{d.isoformat()}"
    
    def get_validation_report(self) -> Dict:
        """Summarize validation results."""
        return {
            "total_records": len(self.records),
            "errors_count": len(self.validation_log),
            "errors": self.validation_log[-10:],  # Last 10
        }
