"""
Decision Fusion Module for AgriCopilot

Combines multiple forecasts into actionable, explainable recommendations.
Outputs include:
- Irrigation schedule (when, how much)
- Fertilizer plan (N, P, K amounts + timing)
- Disease mitigation strategies
- Economic profitability estimate
- Harvest timing
- Confidence scores and limitations

All recommendations are generated with reasoning chains for transparency.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from data_pipeline import AlignedDataFrame, LocationKey
from forecasting import ForecastResult, ForecastingPipeline


class RecommendationConfidence(str, Enum):
    """Confidence levels for recommendations."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


@dataclass
class IrrigationRecommendation:
    """Irrigation schedule and amounts."""
    start_date: date
    end_date: date
    events: List[Dict] = field(default_factory=list)  # [{"date": date, "amount_mm": float}, ...]
    total_mm: float = 0.0
    confidence: RecommendationConfidence = RecommendationConfidence.MODERATE
    reasoning: str = ""


@dataclass
class FertilizerRecommendation:
    """Fertilizer application plan."""
    crop: str
    n_kg_ha: float
    p_kg_ha: float
    k_kg_ha: float
    split_applications: List[Dict] = field(default_factory=list)  # [{"timing": str, "n_kg_ha": float}, ...]
    confidence: RecommendationConfidence = RecommendationConfidence.MODERATE
    reasoning: str = ""


@dataclass
class DiseaseManagementRecommendation:
    """Disease prevention and treatment strategies."""
    high_risk_diseases: List[str]
    preventive_measures: List[str]
    monitoring_frequency_days: int = 7
    intervention_triggers: List[str] = field(default_factory=list)
    confidence: RecommendationConfidence = RecommendationConfidence.MODERATE
    reasoning: str = ""


@dataclass
class HarvestRecommendation:
    """Estimated harvest timing and expected outcome."""
    estimated_harvest_date: date
    expected_yield_kg_ha: float
    expected_yield_ci_lower: float
    expected_yield_ci_upper: float
    expected_market_price_per_kg: Optional[float] = None
    expected_profit_per_ha: Optional[float] = None
    confidence: RecommendationConfidence = RecommendationConfidence.MODERATE
    reasoning: str = ""


@dataclass
class AgricultureDecision:
    """Unified agricultural decision with all recommendations."""
    location: LocationKey
    crop: str
    decision_date: date
    growing_season_length_days: int
    
    irrigation: Optional[IrrigationRecommendation] = None
    fertilizer: Optional[FertilizerRecommendation] = None
    disease_management: Optional[DiseaseManagementRecommendation] = None
    harvest: Optional[HarvestRecommendation] = None
    
    overall_confidence: float = 0.5  # [0, 1]
    data_completeness: float = 0.0  # Fraction of required inputs available
    recommendations_summary: str = ""
    limitations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "location": {"lat": self.location.latitude, "lon": self.location.longitude},
            "crop": self.crop,
            "decision_date": self.decision_date.isoformat(),
            "growing_season_days": self.growing_season_length_days,
            "irrigation": {
                "total_mm": self.irrigation.total_mm,
                "confidence": self.irrigation.confidence.value,
            } if self.irrigation else None,
            "fertilizer": {
                "n_kg_ha": self.fertilizer.n_kg_ha,
                "p_kg_ha": self.fertilizer.p_kg_ha,
                "k_kg_ha": self.fertilizer.k_kg_ha,
                "confidence": self.fertilizer.confidence.value,
            } if self.fertilizer else None,
            "disease_risks": self.disease_management.high_risk_diseases if self.disease_management else [],
            "expected_yield_kg_ha": self.harvest.expected_yield_kg_ha if self.harvest else None,
            "expected_profit_per_ha": self.harvest.expected_profit_per_ha if self.harvest else None,
            "overall_confidence": self.overall_confidence,
            "data_completeness": self.data_completeness,
        }


class DecisionFusionEngine:
    """Fuses forecasts into actionable decisions."""
    
    # Crop-specific parameters (TNAU Agritech data)
    CROP_PARAMS = {
        "rice": {
            "optimal_temp_c": (25, 35),
            "water_need_mm": 1200,
            "growing_days": 120,
            "optimal_ph": (5.5, 7.0),
            "n_kg_ha_target": 100,
            "p_kg_ha_target": 40,
            "k_kg_ha_target": 40,
            "market_price_per_kg": 25,  # INR, approximate
        },
        "maize": {
            "optimal_temp_c": (20, 30),
            "water_need_mm": 600,
            "growing_days": 110,
            "optimal_ph": (5.8, 7.0),
            "n_kg_ha_target": 120,
            "p_kg_ha_target": 50,
            "k_kg_ha_target": 50,
            "market_price_per_kg": 20,
        },
        "millets": {
            "optimal_temp_c": (25, 35),
            "water_need_mm": 400,
            "growing_days": 90,
            "optimal_ph": (6.0, 7.5),
            "n_kg_ha_target": 40,
            "p_kg_ha_target": 20,
            "k_kg_ha_target": 20,
            "market_price_per_kg": 30,
        },
    }
    
    def __init__(self, forecasting_pipeline: ForecastingPipeline):
        self.forecasting_pipeline = forecasting_pipeline
    
    def fuse_and_decide(
        self,
        aligned_data: AlignedDataFrame,
        planting_date: date,
    ) -> AgricultureDecision:
        """
        Main decision-making function:
        1. Run all forecasters
        2. Extract recommendations for irrigation, fertilizer, disease, harvest
        3. Generate unified decision with confidence scores
        4. Explain reasoning for each recommendation
        """
        
        crop = aligned_data.crop
        crop_params = self.CROP_PARAMS.get(crop, self.CROP_PARAMS["rice"])
        
        # Run forecasting pipeline
        forecasts = self.forecasting_pipeline.forecast_all(
            aligned_data,
            days_ahead=30
        )
        
        # Initialize decision object
        decision = AgricultureDecision(
            location=aligned_data.location,
            crop=crop,
            decision_date=aligned_data.date,
            growing_season_length_days=crop_params["growing_days"],
            data_completeness=aligned_data.data_completeness,
        )
        
        # Extract forecasts
        yield_forecasts = forecasts.get("yield", [])
        water_stress_forecasts = forecasts.get("water_stress", [])
        disease_risk_forecasts = forecasts.get("disease_risk", [])
        fertilizer_forecasts = forecasts.get("fertilizer", [])
        
        # Generate recommendations
        if water_stress_forecasts:
            decision.irrigation = self._recommend_irrigation(
                water_stress_forecasts[0],
                crop_params,
                aligned_data,
            )
        
        if fertilizer_forecasts:
            decision.fertilizer = self._recommend_fertilizer(
                fertilizer_forecasts[0],
                crop_params,
                aligned_data,
            )
        
        if disease_risk_forecasts:
            decision.disease_management = self._recommend_disease_management(
                disease_risk_forecasts[0],
                aligned_data,
            )
        
        if yield_forecasts:
            decision.harvest = self._recommend_harvest(
                yield_forecasts[0],
                crop_params,
                planting_date,
                aligned_data,
            )
        
        # Calculate overall confidence
        confidences = [
            item.confidence == RecommendationConfidence.HIGH
            for item in (decision.irrigation, decision.fertilizer, decision.disease_management)
            if item is not None
        ]
        decision.overall_confidence = sum(confidences) / max(1, len(confidences))
        
        # Add limitations
        if aligned_data.data_completeness < 0.5:
            decision.limitations.append("Incomplete data: some data sources unavailable")
        if aligned_data.weather is None:
            decision.limitations.append("No weather data: recommendations may be inaccurate")
        if aligned_data.soil is None:
            decision.limitations.append("No soil data: recommendations may be inaccurate")
        
        # Generate summary
        decision.recommendations_summary = self._generate_summary(decision)
        
        return decision
    
    def _recommend_irrigation(
        self,
        water_stress_forecast: ForecastResult,
        crop_params: Dict,
        aligned_data: AlignedDataFrame,
    ) -> IrrigationRecommendation:
        """Generate irrigation schedule based on water stress forecast."""
        
        stress_index = water_stress_forecast.point_estimate
        
        # Decision logic
        events = []
        total_mm = 0
        reasoning = water_stress_forecast.explanation
        
        if stress_index > 0.6:  # High stress = dry
            # Recommend irrigation
            irrigation_mm = 50  # Default depth
            events.append({
                "date": water_stress_forecast.date,
                "amount_mm": irrigation_mm,
                "justification": f"Water stress high ({stress_index:.2f})",
            })
            total_mm += irrigation_mm
            reasoning += f"\nIrrigation recommended: {irrigation_mm}mm (stress={stress_index:.2f})"
        elif 0.3 < stress_index <= 0.6:  # Moderate
            events.append({
                "date": water_stress_forecast.date,
                "amount_mm": 25,
                "justification": f"Water stress moderate ({stress_index:.2f})",
            })
            total_mm += 25
            reasoning += f"\nLight irrigation: 25mm (stress={stress_index:.2f})"
        else:
            reasoning += "\nNo irrigation needed; adequate soil moisture."
        
        # Determine confidence
        confidence = RecommendationConfidence.MODERATE
        if water_stress_forecast.confidence > 0.7:
            confidence = RecommendationConfidence.HIGH
        
        return IrrigationRecommendation(
            start_date=aligned_data.date,
            end_date=aligned_data.date + timedelta(days=30),
            events=events,
            total_mm=total_mm,
            confidence=confidence,
            reasoning=reasoning,
        )
    
    def _recommend_fertilizer(
        self,
        fertilizer_forecast: ForecastResult,
        crop_params: Dict,
        aligned_data: AlignedDataFrame,
    ) -> FertilizerRecommendation:
        """Generate fertilizer recommendation."""
        
        n_rec = fertilizer_forecast.point_estimate
        p_rec = crop_params.get("p_kg_ha_target", 40)
        k_rec = crop_params.get("k_kg_ha_target", 40)
        
        # Split applications for N (basal + top-dress)
        split_applications = [
            {"timing": "basal (at planting)", "n_kg_ha": n_rec * 0.5},
            {"timing": "top-dress (30 days)", "n_kg_ha": n_rec * 0.5},
        ]
        
        reasoning = fertilizer_forecast.explanation
        reasoning += f"\nN recommendation split: {n_rec*0.5:.0f} kg/ha at planting, {n_rec*0.5:.0f} kg/ha at 30 days"
        
        confidence = RecommendationConfidence.MODERATE
        if aligned_data.soil and aligned_data.soil.nitrogen_ppm:
            confidence = RecommendationConfidence.HIGH
        
        return FertilizerRecommendation(
            crop=aligned_data.crop,
            n_kg_ha=n_rec,
            p_kg_ha=p_rec,
            k_kg_ha=k_rec,
            split_applications=split_applications,
            confidence=confidence,
            reasoning=reasoning,
        )
    
    def _recommend_disease_management(
        self,
        disease_risk_forecast: ForecastResult,
        aligned_data: AlignedDataFrame,
    ) -> DiseaseManagementRecommendation:
        """Generate disease prevention strategy."""
        
        risk = disease_risk_forecast.point_estimate
        
        # Identify high-risk diseases by crop
        high_risk_diseases = []
        if aligned_data.crop == "rice" and risk > 0.6:
            high_risk_diseases = ["Blast", "Sheath rot", "Brown spot"]
        elif aligned_data.crop == "maize" and risk > 0.6:
            high_risk_diseases = ["Leaf blight", "Rust", "Ear rot"]
        
        # Preventive measures
        preventive_measures = [
            "Use resistant varieties",
            "Maintain crop sanitation",
            "Optimize fertilizer use",
            "Avoid water logging",
        ]
        if risk > 0.7:
            preventive_measures.append("Consider fungicide spraying at early disease signs")
        
        monitoring_freq = 3 if risk > 0.7 else 7
        
        reasoning = disease_risk_forecast.explanation
        reasoning += f"\nHigh-risk diseases: {', '.join(high_risk_diseases)}"
        
        confidence = RecommendationConfidence.MODERATE if risk > 0.5 else RecommendationConfidence.LOW
        
        return DiseaseManagementRecommendation(
            high_risk_diseases=high_risk_diseases,
            preventive_measures=preventive_measures,
            monitoring_frequency_days=monitoring_freq,
            confidence=confidence,
            reasoning=reasoning,
        )
    
    def _recommend_harvest(
        self,
        yield_forecast: ForecastResult,
        crop_params: Dict,
        planting_date: date,
        aligned_data: AlignedDataFrame,
    ) -> HarvestRecommendation:
        """Generate harvest timing and economic estimate."""
        
        growing_days = crop_params["growing_days"]
        harvest_date = planting_date + timedelta(days=growing_days)
        
        yield_estimate = yield_forecast.point_estimate
        market_price = aligned_data.market.price_per_kg if aligned_data.market else None
        revenue_per_ha = yield_estimate * market_price if market_price is not None else None
        profit_per_ha = None
        reasoning = yield_forecast.explanation
        reasoning += f"\nHarvest timing: {growing_days} days from planting = {harvest_date.isoformat()}"
        if revenue_per_ha is not None:
            reasoning += f"\nExpected revenue: {yield_estimate:.0f} kg/ha x INR {market_price} = INR {revenue_per_ha:.0f}/ha"
        else:
            reasoning += "\nN/A: no verified live market price is available."
        confidence = RecommendationConfidence.MODERATE
        if yield_forecast.confidence > 0.7:
            confidence = RecommendationConfidence.HIGH
        
        return HarvestRecommendation(
            estimated_harvest_date=harvest_date,
            expected_yield_kg_ha=yield_estimate,
            expected_yield_ci_lower=yield_forecast.lower_ci,
            expected_yield_ci_upper=yield_forecast.upper_ci,
            expected_market_price_per_kg=market_price,
            expected_profit_per_ha=profit_per_ha,
            confidence=confidence,
            reasoning=reasoning,
        )
    
    def _generate_summary(self, decision: AgricultureDecision) -> str:
        """Generate human-readable summary of recommendations."""
        
        summary_lines = [
            f"🌾 Agricultural Decision for {decision.crop.capitalize()} at ({decision.location.latitude:.2f}, {decision.location.longitude:.2f})",
            f"📅 Decision Date: {decision.decision_date.isoformat()}",
            f"Confidence: {decision.overall_confidence:.0%}",
            "",
        ]
        
        if decision.irrigation:
            summary_lines.append(f"💧 Irrigation: {decision.irrigation.total_mm:.0f}mm total ({decision.irrigation.confidence.value})")
        
        if decision.fertilizer:
            summary_lines.append(
                f"🌱 Fertilizer: N={decision.fertilizer.n_kg_ha:.0f}, P={decision.fertilizer.p_kg_ha:.0f}, "
                f"K={decision.fertilizer.k_kg_ha:.0f} kg/ha ({decision.fertilizer.confidence.value})"
            )
        
        if decision.disease_management:
            summary_lines.append(
                f"🦠 Disease Risk: {', '.join(decision.disease_management.high_risk_diseases) or 'Low'} "
                f"({decision.disease_management.confidence.value})"
            )
        
        if decision.harvest:
            profit_str = f" (₹{decision.harvest.expected_profit_per_ha:.0f}/ha profit)" if decision.harvest.expected_profit_per_ha is not None else ""
            summary_lines.append(
                f"🎯 Expected Yield: {decision.harvest.expected_yield_kg_ha:.0f} kg/ha{profit_str} "
                f"({decision.harvest.confidence.value})"
            )
        
        if decision.limitations:
            summary_lines.append("")
            summary_lines.append("⚠️  Limitations:")
            for limitation in decision.limitations:
                summary_lines.append(f"  • {limitation}")
        
        return "\n".join(summary_lines)
