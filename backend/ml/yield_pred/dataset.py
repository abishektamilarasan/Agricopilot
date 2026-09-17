"""
Agricultural Yield Prediction Dataset

Generates realistic synthetic tabular data for training yield prediction models.
Features align with AgriCopilot's existing data pipeline (weather, soil, crop metadata).

Feature set:
    Weather: GDD, rainfall_mm, solar_radiation, avg_temp, humidity, wind_speed,
             heat_stress_days, drought_risk_score
    Soil:    nitrogen_g_kg, phosphorus_g_kg, potassium_g_kg, pH, organic_carbon,
             clay_pct, sand_pct, moisture_pct, CEC
    Crop:    growing_days, water_need_mm, base_temp
    Satellite: NDVI mean
    
Target: yield_tons_ha
"""

import json
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# ── Feature names ─────────────────────────────────────────────
WEATHER_FEATURES = [
    "gdd", "rainfall_mm", "solar_radiation_kwh", "avg_temp_c",
    "humidity_pct", "wind_speed_kmh", "heat_stress_days", "drought_risk_score",
]

SOIL_FEATURES = [
    "nitrogen_g_kg", "phosphorus_g_kg", "potassium_g_kg", "ph",
    "organic_carbon_g_kg", "clay_pct", "sand_pct", "moisture_pct", "cec_cmol_kg",
]

CROP_FEATURES = [
    "growing_days", "water_need_mm", "base_temp_c",
]

SATELLITE_FEATURES = [
    "ndvi_mean",
]

ALL_FEATURES = WEATHER_FEATURES + SOIL_FEATURES + CROP_FEATURES + SATELLITE_FEATURES
TARGET = "yield_tons_ha"

# ── Crop profiles for data generation ─────────────────────────
CROP_PROFILES = {
    "rice": {"avg_yield": 3.5, "std_yield": 0.8, "growing_days": 120, "water_need": 1200, "base_temp": 10},
    "maize": {"avg_yield": 6.0, "std_yield": 1.2, "growing_days": 110, "water_need": 600, "base_temp": 10},
    "sugarcane": {"avg_yield": 100.0, "std_yield": 15.0, "growing_days": 300, "water_need": 2000, "base_temp": 20},
    "cotton": {"avg_yield": 0.5, "std_yield": 0.15, "growing_days": 150, "water_need": 800, "base_temp": 15},
    "groundnut": {"avg_yield": 2.0, "std_yield": 0.5, "growing_days": 120, "water_need": 600, "base_temp": 15},
    "banana": {"avg_yield": 40.0, "std_yield": 8.0, "growing_days": 330, "water_need": 1500, "base_temp": 15},
    "tomato": {"avg_yield": 25.0, "std_yield": 6.0, "growing_days": 100, "water_need": 600, "base_temp": 10},
    "onion": {"avg_yield": 15.0, "std_yield": 4.0, "growing_days": 120, "water_need": 500, "base_temp": 10},
}


def generate_synthetic_yield_data(
    n_samples: int = 2000,
    crops: Optional[List[str]] = None,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic agricultural yield data with realistic feature correlations.
    
    The yield is generated as a function of features with added noise:
        yield = f(weather, soil, crop) + noise
    
    This ensures the ML models learn meaningful patterns rather than random noise.
    """
    rng = np.random.RandomState(seed)
    crops = crops or list(CROP_PROFILES.keys())
    samples_per_crop = n_samples // len(crops)
    
    all_rows = []
    
    for crop_name in crops:
        profile = CROP_PROFILES[crop_name]
        
        for _ in range(samples_per_crop):
            # ── Weather features (correlated) ─────────────────
            avg_temp = rng.normal(27, 4)
            gdd = max(0, (avg_temp - profile["base_temp"]) * profile["growing_days"])
            rainfall = max(0, rng.normal(profile["water_need"] * 0.8, profile["water_need"] * 0.3))
            solar = max(0, rng.normal(5.5, 1.0))
            humidity = np.clip(rng.normal(65, 15), 20, 100)
            wind = max(0, rng.normal(8, 3))
            heat_stress = max(0, int(rng.normal(5, 3)))
            drought_risk = np.clip(1.0 - (rainfall / profile["water_need"]), 0, 1)
            
            # ── Soil features ────────────────────────────────
            nitrogen = max(0, rng.normal(1.5, 0.5))
            phosphorus = max(0, rng.normal(0.8, 0.3))
            potassium = max(0, rng.normal(1.2, 0.4))
            ph = np.clip(rng.normal(6.5, 0.8), 4.0, 9.0)
            organic_carbon = max(0, rng.normal(15, 5))
            clay = np.clip(rng.normal(30, 10), 5, 70)
            sand = np.clip(rng.normal(40, 12), 5, 80)
            moisture = np.clip(rng.normal(35, 10), 5, 70)
            cec = max(0, rng.normal(15, 5))
            
            # ── Crop features ────────────────────────────────
            growing_days = profile["growing_days"] + rng.randint(-10, 11)
            water_need = profile["water_need"]
            base_temp = profile["base_temp"]
            
            # ── Satellite ────────────────────────────────────
            ndvi = np.clip(rng.normal(0.6, 0.15), 0.1, 0.95)
            
            # ── Compute yield (nonlinear function of features) ─
            # Water satisfaction ratio
            water_ratio = min(rainfall / water_need, 1.2)
            # Nutrient score
            nutrient_score = (nitrogen / 2.0 + phosphorus / 1.0 + potassium / 1.5) / 3.0
            nutrient_score = min(nutrient_score, 1.5)
            # pH suitability (bell curve around 6.5)
            ph_factor = np.exp(-0.5 * ((ph - 6.5) / 1.0) ** 2)
            # Temperature suitability
            temp_factor = np.exp(-0.5 * ((avg_temp - 27) / 5.0) ** 2)
            # NDVI health
            ndvi_factor = ndvi / 0.7
            # Heat stress penalty
            heat_penalty = 1.0 - (heat_stress * 0.02)
            
            # Yield = base * modifiers + noise
            base_yield = profile["avg_yield"]
            yield_val = (
                base_yield
                * water_ratio ** 0.4
                * nutrient_score ** 0.3
                * ph_factor ** 0.2
                * temp_factor ** 0.3
                * ndvi_factor ** 0.2
                * heat_penalty
            )
            yield_val += rng.normal(0, profile["std_yield"] * 0.3)
            yield_val = max(0.1, yield_val)
            
            all_rows.append({
                "crop": crop_name,
                "gdd": round(gdd, 1),
                "rainfall_mm": round(rainfall, 1),
                "solar_radiation_kwh": round(solar, 2),
                "avg_temp_c": round(avg_temp, 1),
                "humidity_pct": round(humidity, 1),
                "wind_speed_kmh": round(wind, 1),
                "heat_stress_days": heat_stress,
                "drought_risk_score": round(drought_risk, 3),
                "nitrogen_g_kg": round(nitrogen, 2),
                "phosphorus_g_kg": round(phosphorus, 2),
                "potassium_g_kg": round(potassium, 2),
                "ph": round(ph, 2),
                "organic_carbon_g_kg": round(organic_carbon, 1),
                "clay_pct": round(clay, 1),
                "sand_pct": round(sand, 1),
                "moisture_pct": round(moisture, 1),
                "cec_cmol_kg": round(cec, 1),
                "growing_days": growing_days,
                "water_need_mm": water_need,
                "base_temp_c": base_temp,
                "ndvi_mean": round(ndvi, 3),
                TARGET: round(yield_val, 2),
            })
    
    df = pd.DataFrame(all_rows)
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


def get_train_val_test(
    df: Optional[pd.DataFrame] = None,
    n_samples: int = 2000,
    test_size: float = 0.15,
    val_size: float = 0.15,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split data into train/val/test sets.
    Returns (train_df, val_df, test_df).
    """
    if df is None:
        df = generate_synthetic_yield_data(n_samples=n_samples, seed=seed)
    
    train_df, test_df = train_test_split(df, test_size=test_size, random_state=seed, stratify=df["crop"])
    train_df, val_df = train_test_split(train_df, test_size=val_size / (1 - test_size), random_state=seed, stratify=train_df["crop"])
    
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True), test_df.reset_index(drop=True)


def get_feature_matrix(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract feature matrix X and target vector y from a DataFrame.
    Drops 'crop' column (used for stratification only).
    """
    X = df[ALL_FEATURES].values.astype(np.float32)
    y = df[TARGET].values.astype(np.float32)
    return X, y
