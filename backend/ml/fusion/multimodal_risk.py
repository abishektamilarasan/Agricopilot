"""
Multimodal Disease-Risk Fusion Module

Fuses predictions from multiple modalities into a unified risk assessment:
  - Visual (disease classifier probability)
  - Environmental (weather stress indicators)
  - Soil (nutrient deficiency, pH, moisture)
  - Satellite (NDVI vegetation health)

The fusion uses a weighted Bayesian-inspired approach where each modality
contributes proportionally to its confidence and data availability.
"""

import json
import os
from typing import Dict, List, Optional, Tuple

import numpy as np

from ml import REPORTS_DIR


class MultimodalRiskFusion:
    """
    Fuses risk signals from vision, weather, soil, and satellite modalities
    into a unified disease/stress risk assessment.
    """

    # Default modality weights (sum to 1.0)
    DEFAULT_WEIGHTS = {
        "vision": 0.35,
        "weather": 0.25,
        "soil": 0.20,
        "satellite": 0.20,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        # Normalize weights
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}

    def compute_risk(
        self,
        vision_prob: Optional[float] = None,
        vision_class: Optional[str] = None,
        weather_data: Optional[Dict] = None,
        soil_data: Optional[Dict] = None,
        satellite_data: Optional[Dict] = None,
    ) -> Dict:
        """
        Compute fused multimodal risk score.

        Args:
            vision_prob: Disease probability from vision model (0-1)
            vision_class: Predicted disease class name
            weather_data: Dict with keys like temp, humidity, rainfall, etc.
            soil_data: Dict with keys like ph, moisture, nitrogen, etc.
            satellite_data: Dict with keys like ndvi, etc.

        Returns:
            Fused risk assessment dictionary
        """
        modality_scores = {}
        modality_details = {}
        available_weight = 0.0

        # ── Vision modality ───────────────────────────────────
        if vision_prob is not None:
            disease_risk = self._compute_vision_risk(vision_prob, vision_class)
            modality_scores["vision"] = disease_risk["score"]
            modality_details["vision"] = disease_risk
            available_weight += self.weights["vision"]

        # ── Weather modality ──────────────────────────────────
        if weather_data:
            weather_risk = self._compute_weather_risk(weather_data)
            modality_scores["weather"] = weather_risk["score"]
            modality_details["weather"] = weather_risk
            available_weight += self.weights["weather"]

        # ── Soil modality ─────────────────────────────────────
        if soil_data:
            soil_risk = self._compute_soil_risk(soil_data)
            modality_scores["soil"] = soil_risk["score"]
            modality_details["soil"] = soil_risk
            available_weight += self.weights["soil"]

        # ── Satellite modality ────────────────────────────────
        if satellite_data:
            satellite_risk = self._compute_satellite_risk(satellite_data)
            modality_scores["satellite"] = satellite_risk["score"]
            modality_details["satellite"] = satellite_risk
            available_weight += self.weights["satellite"]

        # ── Weighted fusion ───────────────────────────────────
        if not modality_scores:
            return {
                "fused_risk_score": 0.0,
                "risk_level": "unknown",
                "confidence": 0.0,
                "modalities_used": [],
                "reasoning": "No modality data available.",
            }

        fused_score = 0.0
        for mod, score in modality_scores.items():
            # Re-normalize weight to account for missing modalities
            w = self.weights[mod] / available_weight
            fused_score += w * score

        # Confidence based on data completeness
        confidence = available_weight / sum(self.weights.values())

        # Risk level
        risk_level = self._score_to_level(fused_score)

        # Generate reasoning chain
        reasoning = self._generate_reasoning(modality_details, fused_score, risk_level)

        return {
            "fused_risk_score": round(fused_score, 4),
            "risk_level": risk_level,
            "confidence": round(confidence, 4),
            "modalities_used": list(modality_scores.keys()),
            "modality_scores": {k: round(v, 4) for k, v in modality_scores.items()},
            "modality_weights": {k: round(self.weights[k] / available_weight, 3) for k in modality_scores},
            "modality_details": modality_details,
            "reasoning": reasoning,
            "recommendations": self._generate_recommendations(modality_details, risk_level),
        }

    def _compute_vision_risk(self, prob: float, cls: Optional[str]) -> Dict:
        """Convert vision disease probability to risk score."""
        if cls and cls.lower() == "healthy":
            score = (1 - prob) * 0.3  # Low risk if classified healthy with high confidence
        else:
            score = prob * 0.8 + 0.2  # Higher baseline if disease detected
        
        return {
            "score": np.clip(score, 0, 1),
            "disease_class": cls or "unknown",
            "disease_probability": round(prob, 4),
            "factor": "Visual disease detection",
        }

    def _compute_weather_risk(self, data: Dict) -> Dict:
        """Compute weather-based stress risk."""
        risk_factors = []
        score = 0.0

        # Temperature stress
        temp = data.get("avg_temp_c") or data.get("temperature_current")
        if temp is not None:
            if temp > 38:
                score += 0.3
                risk_factors.append(f"Extreme heat ({temp:.1f}°C)")
            elif temp > 35:
                score += 0.15
                risk_factors.append(f"Heat stress ({temp:.1f}°C)")
            elif temp < 10:
                score += 0.2
                risk_factors.append(f"Cold stress ({temp:.1f}°C)")

        # Humidity (disease-favorable)
        humidity = data.get("humidity_pct") or data.get("humidity")
        if humidity is not None:
            if humidity > 85:
                score += 0.25
                risk_factors.append(f"High humidity ({humidity:.0f}%) — favorable for fungal diseases")
            elif humidity < 30:
                score += 0.1
                risk_factors.append(f"Low humidity ({humidity:.0f}%)")

        # Excessive rainfall / drought
        rainfall = data.get("rainfall_mm") or data.get("precipitation_mm")
        if rainfall is not None:
            if rainfall > 100:
                score += 0.2
                risk_factors.append(f"Heavy rainfall ({rainfall:.0f} mm)")
            elif rainfall < 5:
                score += 0.15
                risk_factors.append(f"Very low rainfall ({rainfall:.1f} mm)")

        # Heat stress days
        heat_days = data.get("heat_stress_days", 0)
        if heat_days > 5:
            score += 0.15
            risk_factors.append(f"{heat_days} heat stress days")

        return {
            "score": np.clip(score, 0, 1),
            "risk_factors": risk_factors,
            "factor": "Weather stress assessment",
        }

    def _compute_soil_risk(self, data: Dict) -> Dict:
        """Compute soil condition risk."""
        risk_factors = []
        score = 0.0

        # pH risk
        ph = data.get("ph")
        if ph is not None:
            if ph < 5.0 or ph > 8.5:
                score += 0.25
                risk_factors.append(f"Extreme pH ({ph:.1f})")
            elif ph < 5.5 or ph > 7.5:
                score += 0.1
                risk_factors.append(f"Suboptimal pH ({ph:.1f})")

        # Moisture
        moisture = data.get("moisture_pct") or data.get("soil_moisture")
        if moisture is not None:
            if moisture < 15:
                score += 0.3
                risk_factors.append(f"Very low soil moisture ({moisture:.0f}%)")
            elif moisture < 25:
                score += 0.15
                risk_factors.append(f"Low soil moisture ({moisture:.0f}%)")
            elif moisture > 65:
                score += 0.2
                risk_factors.append(f"Waterlogged soil ({moisture:.0f}%)")

        # Nitrogen deficiency
        nitrogen = data.get("nitrogen_g_kg")
        if nitrogen is not None and nitrogen < 0.8:
            score += 0.15
            risk_factors.append(f"Low nitrogen ({nitrogen:.1f} g/kg)")

        return {
            "score": np.clip(score, 0, 1),
            "risk_factors": risk_factors,
            "factor": "Soil condition assessment",
        }

    def _compute_satellite_risk(self, data: Dict) -> Dict:
        """Compute satellite/NDVI-based vegetation health risk."""
        risk_factors = []
        score = 0.0

        ndvi = data.get("ndvi_mean") or data.get("current_ndvi")
        if ndvi is not None:
            if ndvi < 0.2:
                score = 0.8
                risk_factors.append(f"Very low NDVI ({ndvi:.2f}) — bare/stressed vegetation")
            elif ndvi < 0.35:
                score = 0.5
                risk_factors.append(f"Low NDVI ({ndvi:.2f}) — unhealthy vegetation")
            elif ndvi < 0.5:
                score = 0.25
                risk_factors.append(f"Moderate NDVI ({ndvi:.2f})")
            else:
                score = 0.1
                risk_factors.append(f"Healthy NDVI ({ndvi:.2f})")

        return {
            "score": np.clip(score, 0, 1),
            "risk_factors": risk_factors,
            "factor": "Satellite vegetation health",
        }

    def _score_to_level(self, score: float) -> str:
        if score >= 0.7:
            return "critical"
        elif score >= 0.5:
            return "high"
        elif score >= 0.3:
            return "moderate"
        else:
            return "low"

    def _generate_reasoning(self, details: Dict, fused: float, level: str) -> str:
        """Generate human-readable reasoning chain."""
        parts = [f"Overall risk level: {level.upper()} (score: {fused:.2f})"]
        
        for mod, d in details.items():
            parts.append(f"\n  [{mod.upper()}] Score: {d['score']:.2f}")
            if "risk_factors" in d:
                for rf in d["risk_factors"]:
                    parts.append(f"    • {rf}")
            if "disease_class" in d:
                parts.append(f"    • Disease: {d['disease_class']} (prob: {d.get('disease_probability', 0):.2f})")
        
        return "\n".join(parts)

    def _generate_recommendations(self, details: Dict, level: str) -> List[str]:
        """Generate actionable recommendations based on risk factors."""
        recs = []
        
        if level in ("critical", "high"):
            recs.append("⚠️ Immediate field inspection recommended within 24 hours.")
        
        if "vision" in details and details["vision"]["score"] > 0.5:
            cls = details["vision"].get("disease_class", "unknown")
            recs.append(f"🔬 Disease detected ({cls}). Consult local agricultural officer.")
        
        if "weather" in details:
            for rf in details["weather"].get("risk_factors", []):
                if "humidity" in rf.lower():
                    recs.append("💨 Apply preventive fungicide due to high humidity.")
                if "heat" in rf.lower():
                    recs.append("🌡️ Increase irrigation frequency to mitigate heat stress.")
        
        if "soil" in details:
            for rf in details["soil"].get("risk_factors", []):
                if "moisture" in rf.lower() and "low" in rf.lower():
                    recs.append("💧 Irrigate immediately — soil moisture critically low.")
                if "nitrogen" in rf.lower():
                    recs.append("🌱 Apply nitrogen-rich fertilizer (urea or DAP).")
        
        if "satellite" in details and details["satellite"]["score"] > 0.4:
            recs.append("🛰️ Satellite indicates vegetation stress. Cross-validate with field observation.")
        
        if not recs:
            recs.append("✅ Conditions are favorable. Continue regular monitoring.")
        
        return recs
