"""
AgriCopilot Configuration
Central configuration for all services, APIs, and model settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings with sensible defaults."""

    # --- LLM Providers (Groq Cloud & Local Ollama) ---
    USE_GROQ_API: int = int(os.getenv("USE_GROQ_API", "1"))
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # --- Ollama Fallback ---
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "mistral")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

    # --- API Base URLs (all free, no keys) ---
    OPEN_METEO_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPEN_METEO_HISTORICAL_URL: str = "https://archive-api.open-meteo.com/v1/archive"
    NASA_POWER_URL: str = "https://power.larc.nasa.gov/api/temporal/daily/point"
    SOILGRIDS_URL: str = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    FAOSTAT_URL: str = "https://www.fao.org/faostat/api/v1"

    # --- ChromaDB ---
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    # --- Defaults ---
    DEFAULT_LAT: float = 20.5937   # India center
    DEFAULT_LON: float = 78.9629
    DEFAULT_CROP: str = "rice"
    DEFAULT_COUNTRY: str = "India"

    # --- Supported crops with growing parameters ---
    # Data Source: TNAU Agritech Portal (agritech.tnau.ac.in)
    SUPPORTED_CROPS: dict = {
        "rice": {
            "name": "Rice", "base_temp_c": 10, "optimal_temp_c": (25, 35),
            "water_need_mm": 1200, "growing_days": 120, "optimal_ph": (5.5, 7.0),
        },
        "maize": {
            "name": "Maize", "base_temp_c": 10, "optimal_temp_c": (20, 30),
            "water_need_mm": 600, "growing_days": 110, "optimal_ph": (5.8, 7.0),
        },
        "millets": {
            "name": "Millets", "base_temp_c": 12, "optimal_temp_c": (25, 35),
            "water_need_mm": 400, "growing_days": 90, "optimal_ph": (6.0, 7.5),
        },
        "sugarcane": {
            "name": "Sugarcane", "base_temp_c": 20, "optimal_temp_c": (27, 35),
            "water_need_mm": 2000, "growing_days": 300, "optimal_ph": (6.0, 7.5),
        },
        "banana": {
            "name": "Banana", "base_temp_c": 15, "optimal_temp_c": (26, 30),
            "water_need_mm": 1500, "growing_days": 330, "optimal_ph": (5.5, 7.0),
        },
        "cotton": {
            "name": "Cotton", "base_temp_c": 15, "optimal_temp_c": (21, 30),
            "water_need_mm": 800, "growing_days": 150, "optimal_ph": (6.0, 8.0),
        },
        "groundnut": {
            "name": "Groundnut", "base_temp_c": 15, "optimal_temp_c": (25, 30),
            "water_need_mm": 600, "growing_days": 120, "optimal_ph": (6.0, 6.5),
        },
        "tomato": {
            "name": "Tomato", "base_temp_c": 10, "optimal_temp_c": (21, 24),
            "water_need_mm": 600, "growing_days": 100, "optimal_ph": (6.0, 6.8),
        },
        "onion": {
            "name": "Onion", "base_temp_c": 10, "optimal_temp_c": (15, 25),
            "water_need_mm": 500, "growing_days": 120, "optimal_ph": (6.0, 7.0),
        },
        "mango": {
            "name": "Mango", "base_temp_c": 20, "optimal_temp_c": (24, 30),
            "water_need_mm": 1000, "growing_days": 365, "optimal_ph": (5.5, 7.5),
        },
    }


settings = Settings()
