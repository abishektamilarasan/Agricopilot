"""
Explainable AI Module for AgriCopilot
─────────────────────────────────────
Implements:
  1. Dempster-Shafer evidence fusion for multi-source uncertainty quantification
  2. Multi-dimensional risk heatmap (6 risk categories)
  3. Chain-of-thought audit trail for full AI transparency
  4. Composite "Field Health Score" (0-100)

Theory:
  Dempster-Shafer theory generalises Bayesian probability by allowing
  explicit representation of *ignorance*.  Each data source produces a
  Basic Probability Assignment (BPA) over {Risk, Safe, Uncertain}.
  Sources are combined with Dempster's rule of combination, and the
  resulting *belief* and *plausibility* intervals give a principled
  measure of risk that distinguishes "we think it's safe" from
  "we have no data".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from models.schemas import WeatherData, SoilData, MarketData, NASAPowerData, SatelliteData


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Structures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class BPA:
    """Basic Probability Assignment (mass function) over the frame {Risk, Safe}.

    m_risk      – mass assigned to the singleton {Risk}
    m_safe      – mass assigned to the singleton {Safe}
    m_uncertain – mass assigned to the full frame {Risk, Safe} (ignorance)

    Invariant: m_risk + m_safe + m_uncertain == 1.0
    """
    m_risk: float = 0.0
    m_safe: float = 0.0
    m_uncertain: float = 1.0  # total ignorance by default

    def belief_risk(self) -> float:
        """Lower bound probability of Risk (Bel)."""
        return self.m_risk

    def plausibility_risk(self) -> float:
        """Upper bound probability of Risk (Pl)."""
        return self.m_risk + self.m_uncertain

    def belief_safe(self) -> float:
        return self.m_safe

    def plausibility_safe(self) -> float:
        return self.m_safe + self.m_uncertain


@dataclass
class ReasoningStep:
    """A single step in the chain-of-thought audit trail."""
    step_number: int
    data_source: str
    observation: str
    interpretation: str
    risk_contribution: float  # how much this step shifted the risk score
    confidence: float         # how confident this individual step is


@dataclass
class RiskDimension:
    """Assessment of a single risk category."""
    name: str                           # e.g. "drought", "flood", "pest"
    score: float                        # 0-100 risk score
    severity: str                       # "low" | "moderate" | "high" | "critical"
    belief_interval: Tuple[float, float]  # (Bel, Pl) from Dempster-Shafer
    reasoning_chain: List[ReasoningStep]
    data_sources_used: List[str]
    data_quality: str                   # "complete" | "partial" | "unavailable"


@dataclass
class RiskDashboardResult:
    """Full output of the Explainable AI Risk Dashboard."""
    field_health_score: float           # 0-100 composite
    health_grade: str                   # A/B/C/D/F
    risk_dimensions: List[RiskDimension]
    chain_of_thought: List[ReasoningStep]  # global reasoning trail
    fusion_method: str = "Dempster-Shafer Evidence Theory"
    timestamp: str = ""
    data_completeness: float = 0.0      # 0-1 fraction

    def to_dict(self) -> dict:
        return {
            "field_health_score": round(self.field_health_score, 1),
            "health_grade": self.health_grade,
            "fusion_method": self.fusion_method,
            "data_completeness": round(self.data_completeness, 2),
            "timestamp": self.timestamp,
            "risk_dimensions": [
                {
                    "name": rd.name,
                    "score": round(rd.score, 1),
                    "severity": rd.severity,
                    "belief_interval": [round(rd.belief_interval[0], 3), round(rd.belief_interval[1], 3)],
                    "data_quality": rd.data_quality,
                    "data_sources_used": rd.data_sources_used,
                    "reasoning_chain": [
                        {
                            "step": rs.step_number,
                            "source": rs.data_source,
                            "observation": rs.observation,
                            "interpretation": rs.interpretation,
                            "risk_contribution": round(rs.risk_contribution, 2),
                            "confidence": round(rs.confidence, 2),
                        }
                        for rs in rd.reasoning_chain
                    ],
                }
                for rd in self.risk_dimensions
            ],
            "chain_of_thought": [
                {
                    "step": rs.step_number,
                    "source": rs.data_source,
                    "observation": rs.observation,
                    "interpretation": rs.interpretation,
                    "risk_contribution": round(rs.risk_contribution, 2),
                    "confidence": round(rs.confidence, 2),
                }
                for rs in self.chain_of_thought
            ],
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dempster-Shafer Combination
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def combine_bpa(bpa1: BPA, bpa2: BPA) -> BPA:
    """Combine two independent BPAs using Dempster's rule of combination.

    The conflict factor K captures the degree of disagreement between sources.
    When K == 1.0 the sources totally contradict and we fall back to maximum
    ignorance.
    """
    # Compute all pairwise intersections
    # {Risk} ∩ {Risk} = {Risk}
    rr = bpa1.m_risk * bpa2.m_risk
    # {Safe} ∩ {Safe} = {Safe}
    ss = bpa1.m_safe * bpa2.m_safe
    # {Risk} ∩ {Safe} = ∅  (conflict)
    rs = bpa1.m_risk * bpa2.m_safe
    sr = bpa1.m_safe * bpa2.m_risk
    # Θ ∩ X = X
    ru = bpa1.m_risk * bpa2.m_uncertain
    ur = bpa1.m_uncertain * bpa2.m_risk
    su = bpa1.m_safe * bpa2.m_uncertain
    us = bpa1.m_uncertain * bpa2.m_safe
    uu = bpa1.m_uncertain * bpa2.m_uncertain

    conflict = rs + sr  # mass assigned to empty set
    if conflict >= 1.0:
        # Total conflict — sources completely disagree
        return BPA(m_risk=0.0, m_safe=0.0, m_uncertain=1.0)

    normaliser = 1.0 / (1.0 - conflict)
    return BPA(
        m_risk=normaliser * (rr + ru + ur),
        m_safe=normaliser * (ss + su + us),
        m_uncertain=normaliser * uu,
    )


def combine_multiple_bpas(bpas: List[BPA]) -> BPA:
    """Combine a list of BPAs sequentially."""
    if not bpas:
        return BPA()  # total ignorance
    result = bpas[0]
    for bpa in bpas[1:]:
        result = combine_bpa(result, bpa)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Risk Assessors (one per dimension)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _severity_label(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "moderate"
    return "low"


def _assess_drought_risk(
    weather: Optional[WeatherData],
    nasa: Optional[NASAPowerData],
    satellite: Optional[SatelliteData],
) -> RiskDimension:
    """Drought risk from precipitation deficit, ET0, NDVI, and soil moisture."""
    bpas: List[BPA] = []
    steps: List[ReasoningStep] = []
    sources: List[str] = []
    step_n = 0

    # --- Weather evidence ---
    if weather and weather.precipitation_mm is not None and weather.evapotranspiration_mm is not None:
        sources.append(f"weather ({weather.source})")
        deficit = weather.evapotranspiration_mm - weather.precipitation_mm
        step_n += 1

        if deficit > 30:
            bpa = BPA(m_risk=0.75, m_safe=0.05, m_uncertain=0.20)
            interp = f"Severe water deficit ({deficit:.1f}mm). ET0 far exceeds rainfall — high drought signal."
        elif deficit > 10:
            bpa = BPA(m_risk=0.50, m_safe=0.15, m_uncertain=0.35)
            interp = f"Moderate water deficit ({deficit:.1f}mm). More water leaving than entering."
        elif deficit > 0:
            bpa = BPA(m_risk=0.25, m_safe=0.30, m_uncertain=0.45)
            interp = f"Slight deficit ({deficit:.1f}mm). Borderline — monitor closely."
        else:
            bpa = BPA(m_risk=0.05, m_safe=0.70, m_uncertain=0.25)
            interp = f"Water surplus ({abs(deficit):.1f}mm). Rainfall exceeds evapotranspiration."

        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source="Open-Meteo Weather",
            observation=f"7-day precipitation = {weather.precipitation_mm:.1f}mm, ET0 = {weather.evapotranspiration_mm:.1f}mm, deficit = {deficit:.1f}mm",
            interpretation=interp, risk_contribution=bpa.m_risk, confidence=0.75,
        ))

    # --- Drought risk enum from weather ---
    if weather and weather.drought_risk:
        step_n += 1
        dr_val = weather.drought_risk.value
        risk_map = {"low": 0.10, "moderate": 0.40, "high": 0.70, "critical": 0.90}
        r = risk_map.get(dr_val, 0.30)
        bpa = BPA(m_risk=r, m_safe=max(0, 0.90 - r), m_uncertain=0.10)
        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source="Weather Drought Index",
            observation=f"Computed drought risk level = '{dr_val}'",
            interpretation=f"Weather-based drought index classifies risk as {dr_val}.",
            risk_contribution=r, confidence=0.70,
        ))

    # --- Satellite NDVI evidence ---
    if satellite and satellite.current_ndvi is not None:
        sources.append(f"satellite ({satellite.source})")
        ndvi = satellite.current_ndvi
        step_n += 1

        if ndvi < 0.2:
            bpa = BPA(m_risk=0.80, m_safe=0.05, m_uncertain=0.15)
            interp = f"Very low NDVI ({ndvi:.2f}) — vegetation severely stressed or absent."
        elif ndvi < 0.4:
            bpa = BPA(m_risk=0.50, m_safe=0.15, m_uncertain=0.35)
            interp = f"Below-average NDVI ({ndvi:.2f}) — possible water stress visible from space."
        elif ndvi < 0.6:
            bpa = BPA(m_risk=0.20, m_safe=0.40, m_uncertain=0.40)
            interp = f"Moderate NDVI ({ndvi:.2f}) — vegetation appears fair."
        else:
            bpa = BPA(m_risk=0.05, m_safe=0.75, m_uncertain=0.20)
            interp = f"Strong NDVI ({ndvi:.2f}) — healthy, dense vegetation canopy."

        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source="Agromonitoring Satellite",
            observation=f"Current NDVI = {ndvi:.2f}, health status = {satellite.health_status}",
            interpretation=interp, risk_contribution=bpa.m_risk, confidence=0.80,
        ))

    # --- Fuse ---
    if not bpas:
        return RiskDimension(
            name="drought", score=0, severity="low",
            belief_interval=(0.0, 1.0), reasoning_chain=[], data_sources_used=[],
            data_quality="unavailable",
        )

    fused = combine_multiple_bpas(bpas)
    score = fused.belief_risk() * 100
    return RiskDimension(
        name="drought", score=score, severity=_severity_label(score),
        belief_interval=(fused.belief_risk(), fused.plausibility_risk()),
        reasoning_chain=steps, data_sources_used=sources,
        data_quality="complete" if len(bpas) >= 2 else "partial",
    )


def _assess_flood_risk(weather: Optional[WeatherData]) -> RiskDimension:
    """Flood risk from excessive precipitation and soil saturation."""
    bpas: List[BPA] = []
    steps: List[ReasoningStep] = []
    sources: List[str] = []
    step_n = 0

    if weather and weather.precipitation_mm is not None:
        sources.append(f"weather ({weather.source})")
        precip = weather.precipitation_mm
        step_n += 1

        if precip > 150:
            bpa = BPA(m_risk=0.85, m_safe=0.05, m_uncertain=0.10)
            interp = f"Extreme rainfall ({precip:.0f}mm in 7 days) — waterlogging and flooding very likely."
        elif precip > 80:
            bpa = BPA(m_risk=0.55, m_safe=0.15, m_uncertain=0.30)
            interp = f"Heavy rainfall ({precip:.0f}mm) — moderate flood/waterlogging risk."
        elif precip > 40:
            bpa = BPA(m_risk=0.20, m_safe=0.40, m_uncertain=0.40)
            interp = f"Moderate rainfall ({precip:.0f}mm) — unlikely to cause flooding."
        else:
            bpa = BPA(m_risk=0.05, m_safe=0.80, m_uncertain=0.15)
            interp = f"Low rainfall ({precip:.0f}mm) — no flood risk."

        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source="Open-Meteo Weather",
            observation=f"7-day cumulative precipitation = {precip:.0f}mm",
            interpretation=interp, risk_contribution=bpa.m_risk, confidence=0.75,
        ))

    if weather and weather.humidity is not None and weather.humidity > 85:
        step_n += 1
        bpa = BPA(m_risk=0.35, m_safe=0.25, m_uncertain=0.40)
        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source="Open-Meteo Weather",
            observation=f"Humidity = {weather.humidity:.0f}%",
            interpretation="Very high humidity supports waterlogging conditions.",
            risk_contribution=0.35, confidence=0.55,
        ))

    if not bpas:
        return RiskDimension(name="flood", score=0, severity="low",
                             belief_interval=(0.0, 1.0), reasoning_chain=[], data_sources_used=[],
                             data_quality="unavailable")

    fused = combine_multiple_bpas(bpas)
    score = fused.belief_risk() * 100
    return RiskDimension(
        name="flood", score=score, severity=_severity_label(score),
        belief_interval=(fused.belief_risk(), fused.plausibility_risk()),
        reasoning_chain=steps, data_sources_used=sources,
        data_quality="complete" if len(bpas) >= 2 else "partial",
    )


def _assess_pest_risk(weather: Optional[WeatherData], crop: str) -> RiskDimension:
    """Pest infestation risk from temperature + humidity + crop type."""
    bpas: List[BPA] = []
    steps: List[ReasoningStep] = []
    sources: List[str] = []
    step_n = 0

    if weather and weather.temperature_current is not None and weather.humidity is not None:
        sources.append(f"weather ({weather.source})")
        temp = weather.temperature_current
        hum = weather.humidity
        step_n += 1

        # Pests thrive in warm, humid conditions
        temp_factor = max(0, min(1, (temp - 20) / 15))  # 0 at 20°C, 1 at 35°C
        hum_factor = max(0, min(1, (hum - 50) / 40))    # 0 at 50%, 1 at 90%
        combined = 0.5 * temp_factor + 0.5 * hum_factor

        bpa = BPA(m_risk=combined * 0.80, m_safe=(1 - combined) * 0.60, m_uncertain=max(0.10, 1 - combined * 0.80 - (1 - combined) * 0.60))
        # Normalise
        total = bpa.m_risk + bpa.m_safe + bpa.m_uncertain
        bpa = BPA(m_risk=bpa.m_risk / total, m_safe=bpa.m_safe / total, m_uncertain=bpa.m_uncertain / total)
        bpas.append(bpa)

        steps.append(ReasoningStep(
            step_number=step_n, data_source="Open-Meteo Weather",
            observation=f"Temperature = {temp:.1f}°C, Humidity = {hum:.0f}%",
            interpretation=f"Pest-conducive index = {combined:.2f}. Warm + humid conditions {'strongly ' if combined > 0.6 else ''}favour pest proliferation for {crop}.",
            risk_contribution=bpa.m_risk, confidence=0.60,
        ))

    # Crop-specific boost
    high_pest_crops = {"rice", "cotton", "tomato", "banana"}
    if crop.lower() in high_pest_crops and bpas:
        step_n += 1
        bpa = BPA(m_risk=0.30, m_safe=0.20, m_uncertain=0.50)
        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source="Crop Profile (TNAU)",
            observation=f"Crop '{crop}' is classified as high pest-susceptibility.",
            interpretation=f"{crop.capitalize()} is historically prone to pest attacks in South India.",
            risk_contribution=0.30, confidence=0.65,
        ))

    if not bpas:
        return RiskDimension(name="pest", score=0, severity="low",
                             belief_interval=(0.0, 1.0), reasoning_chain=[], data_sources_used=[],
                             data_quality="unavailable")

    fused = combine_multiple_bpas(bpas)
    score = fused.belief_risk() * 100
    return RiskDimension(
        name="pest", score=score, severity=_severity_label(score),
        belief_interval=(fused.belief_risk(), fused.plausibility_risk()),
        reasoning_chain=steps, data_sources_used=sources,
        data_quality="partial",
    )


def _assess_disease_risk(weather: Optional[WeatherData], soil: Optional[SoilData], crop: str) -> RiskDimension:
    """Crop disease risk from temperature, humidity, soil pH, and crop profile."""
    bpas: List[BPA] = []
    steps: List[ReasoningStep] = []
    sources: List[str] = []
    step_n = 0

    # Temperature window for fungal diseases
    if weather and weather.temperature_current is not None:
        sources.append(f"weather ({weather.source})")
        temp = weather.temperature_current
        step_n += 1

        # Rice blast optimal range: 20-28°C
        if 20 <= temp <= 28:
            bpa = BPA(m_risk=0.70, m_safe=0.10, m_uncertain=0.20)
            interp = f"Temperature {temp:.1f}°C is in the optimal range for fungal pathogens (20-28°C)."
        elif 15 <= temp <= 32:
            bpa = BPA(m_risk=0.35, m_safe=0.30, m_uncertain=0.35)
            interp = f"Temperature {temp:.1f}°C is marginal for most pathogens."
        else:
            bpa = BPA(m_risk=0.10, m_safe=0.65, m_uncertain=0.25)
            interp = f"Temperature {temp:.1f}°C is outside the pathogen growth window."

        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source="Open-Meteo Weather",
            observation=f"Current temperature = {temp:.1f}°C",
            interpretation=interp, risk_contribution=bpa.m_risk, confidence=0.70,
        ))

    # Humidity
    if weather and weather.humidity is not None:
        hum = weather.humidity
        step_n += 1

        if hum > 85:
            bpa = BPA(m_risk=0.65, m_safe=0.10, m_uncertain=0.25)
            interp = f"Humidity {hum:.0f}% creates leaf wetness ideal for spore germination."
        elif hum > 70:
            bpa = BPA(m_risk=0.30, m_safe=0.30, m_uncertain=0.40)
            interp = f"Humidity {hum:.0f}% is moderate — some disease pressure possible."
        else:
            bpa = BPA(m_risk=0.10, m_safe=0.60, m_uncertain=0.30)
            interp = f"Humidity {hum:.0f}% — dry conditions suppress most fungal diseases."

        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source="Open-Meteo Weather",
            observation=f"Relative humidity = {hum:.0f}%",
            interpretation=interp, risk_contribution=bpa.m_risk, confidence=0.65,
        ))

    # Soil pH deviation (extreme pH increases root disease risk)
    if soil and soil.ph is not None:
        sources.append(f"soil ({soil.source})")
        step_n += 1

        if soil.ph < 5.0 or soil.ph > 8.0:
            bpa = BPA(m_risk=0.45, m_safe=0.15, m_uncertain=0.40)
            interp = f"Soil pH {soil.ph:.1f} is extreme — root disease susceptibility increases."
        else:
            bpa = BPA(m_risk=0.10, m_safe=0.55, m_uncertain=0.35)
            interp = f"Soil pH {soil.ph:.1f} is within normal range — low root disease risk from pH."

        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source="SoilGrids",
            observation=f"Soil pH = {soil.ph:.1f}",
            interpretation=interp, risk_contribution=bpa.m_risk, confidence=0.55,
        ))

    if not bpas:
        return RiskDimension(name="disease", score=0, severity="low",
                             belief_interval=(0.0, 1.0), reasoning_chain=[], data_sources_used=[],
                             data_quality="unavailable")

    fused = combine_multiple_bpas(bpas)
    score = fused.belief_risk() * 100
    return RiskDimension(
        name="disease", score=score, severity=_severity_label(score),
        belief_interval=(fused.belief_risk(), fused.plausibility_risk()),
        reasoning_chain=steps, data_sources_used=sources,
        data_quality="complete" if len(bpas) >= 3 else "partial",
    )


def _assess_market_risk(market: Optional[MarketData]) -> RiskDimension:
    """Market crash / price volatility risk."""
    bpas: List[BPA] = []
    steps: List[ReasoningStep] = []
    sources: List[str] = []
    step_n = 0

    if market and market.source != "unavailable":
        sources.append(f"market ({market.source})")
        step_n += 1

        trend = (market.price_trend or "").lower()
        if "down" in trend or "falling" in trend or "crash" in trend:
            bpa = BPA(m_risk=0.65, m_safe=0.10, m_uncertain=0.25)
            interp = f"Price trend is '{market.price_trend}' — bearish market signal."
        elif "up" in trend or "rising" in trend:
            bpa = BPA(m_risk=0.10, m_safe=0.65, m_uncertain=0.25)
            interp = f"Price trend is '{market.price_trend}' — bullish market signal."
        else:
            bpa = BPA(m_risk=0.25, m_safe=0.25, m_uncertain=0.50)
            interp = f"Price trend is '{market.price_trend or 'unknown'}' — high uncertainty."

        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source=market.source,
            observation=f"Crop = {market.crop}, price trend = '{market.price_trend or 'N/A'}'",
            interpretation=interp, risk_contribution=bpa.m_risk, confidence=0.50,
        ))

        if market.profitability_score is not None:
            step_n += 1
            ps = market.profitability_score
            if ps < 30:
                bpa = BPA(m_risk=0.60, m_safe=0.10, m_uncertain=0.30)
                interp = f"Profitability score {ps}/100 is low — poor economic outlook."
            elif ps < 60:
                bpa = BPA(m_risk=0.30, m_safe=0.30, m_uncertain=0.40)
                interp = f"Profitability score {ps}/100 is moderate."
            else:
                bpa = BPA(m_risk=0.10, m_safe=0.65, m_uncertain=0.25)
                interp = f"Profitability score {ps}/100 is good — healthy margins."

            bpas.append(bpa)
            steps.append(ReasoningStep(
                step_number=step_n, data_source=market.source,
                observation=f"Profitability score = {ps}/100",
                interpretation=interp, risk_contribution=bpa.m_risk, confidence=0.55,
            ))
    else:
        step_n += 1
        steps.append(ReasoningStep(
            step_number=step_n, data_source="Market API",
            observation="Market data is unavailable.",
            interpretation="Cannot assess market risk — full ignorance assigned.",
            risk_contribution=0.0, confidence=0.0,
        ))

    if not bpas:
        return RiskDimension(name="market_crash", score=0, severity="low",
                             belief_interval=(0.0, 1.0), reasoning_chain=steps, data_sources_used=sources,
                             data_quality="unavailable")

    fused = combine_multiple_bpas(bpas)
    score = fused.belief_risk() * 100
    return RiskDimension(
        name="market_crash", score=score, severity=_severity_label(score),
        belief_interval=(fused.belief_risk(), fused.plausibility_risk()),
        reasoning_chain=steps, data_sources_used=sources,
        data_quality="partial",
    )


def _assess_yield_loss_risk(
    weather: Optional[WeatherData],
    soil: Optional[SoilData],
    satellite: Optional[SatelliteData],
    crop: str,
) -> RiskDimension:
    """Yield loss risk — composite of heat stress, soil fertility, and vegetation health."""
    bpas: List[BPA] = []
    steps: List[ReasoningStep] = []
    sources: List[str] = []
    step_n = 0

    # Heat stress
    if weather and weather.heat_stress_days is not None:
        sources.append(f"weather ({weather.source})")
        hsd = weather.heat_stress_days
        step_n += 1

        if hsd >= 5:
            bpa = BPA(m_risk=0.70, m_safe=0.10, m_uncertain=0.20)
            interp = f"{hsd} heat stress days — significant yield penalty expected."
        elif hsd >= 2:
            bpa = BPA(m_risk=0.35, m_safe=0.25, m_uncertain=0.40)
            interp = f"{hsd} heat stress days — moderate yield impact possible."
        else:
            bpa = BPA(m_risk=0.10, m_safe=0.60, m_uncertain=0.30)
            interp = f"{hsd} heat stress days — minimal yield impact."

        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source="Open-Meteo Weather",
            observation=f"Heat stress days (>35°C) in forecast = {hsd}",
            interpretation=interp, risk_contribution=bpa.m_risk, confidence=0.65,
        ))

    # Soil fertility
    if soil and soil.fertility_score is not None:
        sources.append(f"soil ({soil.source})")
        fs = soil.fertility_score
        step_n += 1

        if fs < 30:
            bpa = BPA(m_risk=0.60, m_safe=0.10, m_uncertain=0.30)
            interp = f"Fertility score {fs}/100 is poor — expect below-average yields without amendment."
        elif fs < 60:
            bpa = BPA(m_risk=0.25, m_safe=0.35, m_uncertain=0.40)
            interp = f"Fertility score {fs}/100 is moderate — standard yields achievable."
        else:
            bpa = BPA(m_risk=0.10, m_safe=0.65, m_uncertain=0.25)
            interp = f"Fertility score {fs}/100 is good — soil can support high yields."

        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source="SoilGrids",
            observation=f"Soil fertility score = {fs}/100",
            interpretation=interp, risk_contribution=bpa.m_risk, confidence=0.60,
        ))

    # NDVI (vegetation vigour)
    if satellite and satellite.current_ndvi is not None:
        sources.append(f"satellite ({satellite.source})")
        ndvi = satellite.current_ndvi
        step_n += 1

        if ndvi < 0.3:
            bpa = BPA(m_risk=0.65, m_safe=0.10, m_uncertain=0.25)
            interp = f"NDVI {ndvi:.2f} indicates poor crop vigour — yield loss likely."
        elif ndvi < 0.5:
            bpa = BPA(m_risk=0.30, m_safe=0.30, m_uncertain=0.40)
            interp = f"NDVI {ndvi:.2f} indicates moderate vigour."
        else:
            bpa = BPA(m_risk=0.10, m_safe=0.70, m_uncertain=0.20)
            interp = f"NDVI {ndvi:.2f} indicates strong crop vigour — on track for good yield."

        bpas.append(bpa)
        steps.append(ReasoningStep(
            step_number=step_n, data_source="Agromonitoring Satellite",
            observation=f"Current NDVI = {ndvi:.2f}",
            interpretation=interp, risk_contribution=bpa.m_risk, confidence=0.75,
        ))

    if not bpas:
        return RiskDimension(name="yield_loss", score=0, severity="low",
                             belief_interval=(0.0, 1.0), reasoning_chain=[], data_sources_used=[],
                             data_quality="unavailable")

    fused = combine_multiple_bpas(bpas)
    score = fused.belief_risk() * 100
    return RiskDimension(
        name="yield_loss", score=score, severity=_severity_label(score),
        belief_interval=(fused.belief_risk(), fused.plausibility_risk()),
        reasoning_chain=steps, data_sources_used=sources,
        data_quality="complete" if len(bpas) >= 3 else "partial",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Composite Field Health Score
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _compute_field_health_score(dimensions: List[RiskDimension]) -> Tuple[float, str]:
    """
    Compute a single composite field health score (0-100) from all risk dimensions.
    Health = 100 − weighted_avg(risk_scores).
    Weights emphasise agronomically critical dimensions.
    """
    weights = {
        "drought": 0.25,
        "flood": 0.15,
        "pest": 0.15,
        "disease": 0.20,
        "market_crash": 0.10,
        "yield_loss": 0.15,
    }

    total_weight = 0.0
    weighted_risk = 0.0
    for dim in dimensions:
        w = weights.get(dim.name, 0.10)
        weighted_risk += w * dim.score
        total_weight += w

    if total_weight == 0:
        return 50.0, "C"

    avg_risk = weighted_risk / total_weight
    health = max(0, min(100, 100 - avg_risk))

    if health >= 80:
        grade = "A"
    elif health >= 60:
        grade = "B"
    elif health >= 40:
        grade = "C"
    elif health >= 20:
        grade = "D"
    else:
        grade = "F"

    return health, grade


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Public Entry Point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_risk_dashboard(
    crop: str,
    weather: Optional[WeatherData] = None,
    soil: Optional[SoilData] = None,
    market: Optional[MarketData] = None,
    nasa: Optional[NASAPowerData] = None,
    satellite: Optional[SatelliteData] = None,
) -> RiskDashboardResult:
    """
    Main entry point — generates the full Explainable AI Risk Dashboard.

    Returns a RiskDashboardResult containing:
      - 6-dimension risk heatmap
      - Dempster-Shafer fused scores with belief intervals
      - Per-dimension chain-of-thought reasoning
      - Composite field health score (0-100) with letter grade
    """

    # Assess each risk dimension
    dimensions = [
        _assess_drought_risk(weather, nasa, satellite),
        _assess_flood_risk(weather),
        _assess_pest_risk(weather, crop),
        _assess_disease_risk(weather, soil, crop),
        _assess_market_risk(market),
        _assess_yield_loss_risk(weather, soil, satellite, crop),
    ]

    # Composite score
    health_score, grade = _compute_field_health_score(dimensions)

    # Build global chain-of-thought (flatten + renumber)
    global_chain: List[ReasoningStep] = []
    step_counter = 0
    for dim in dimensions:
        for rs in dim.reasoning_chain:
            step_counter += 1
            global_chain.append(ReasoningStep(
                step_number=step_counter,
                data_source=rs.data_source,
                observation=rs.observation,
                interpretation=rs.interpretation,
                risk_contribution=rs.risk_contribution,
                confidence=rs.confidence,
            ))

    # Data completeness
    available = sum(1 for x in [weather, soil, market, nasa, satellite] if x is not None)
    completeness = available / 5.0

    return RiskDashboardResult(
        field_health_score=health_score,
        health_grade=grade,
        risk_dimensions=dimensions,
        chain_of_thought=global_chain,
        data_completeness=completeness,
        timestamp=datetime.now().isoformat(),
    )
