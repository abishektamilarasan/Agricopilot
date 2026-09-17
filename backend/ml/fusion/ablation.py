"""
Ablation Study Module

Evaluates the contribution of each modality (weather, soil, NDVI, vision)
to the overall disease-risk assessment through systematic ablation.

Models compared:
  A: Weather only
  B: Weather + Soil
  C: Weather + Soil + NDVI
  D: Weather + Soil + NDVI + Vision (full model)

Metrics: Mean risk score accuracy, risk level agreement, Spearman correlation.
Results saved to reports/ablation_results.json and reports/ablation_results.csv.
"""

import csv
import json
import os
from typing import Dict, List

import numpy as np
from scipy import stats

from ml import REPORTS_DIR
from ml.fusion.multimodal_risk import MultimodalRiskFusion


def generate_ablation_scenarios(n_scenarios: int = 200, seed: int = 42) -> List[Dict]:
    """
    Generate synthetic multimodal scenarios for ablation testing.
    Each scenario has ground-truth risk signals from each modality.
    """
    rng = np.random.RandomState(seed)
    scenarios = []
    
    disease_classes = ["healthy", "leaf_blast", "bacterial_blight", "brown_spot", "rust"]
    
    for i in range(n_scenarios):
        # Ground truth risk level (drives data generation)
        true_risk = rng.choice(["low", "moderate", "high", "critical"], p=[0.3, 0.3, 0.25, 0.15])
        
        base_risk = {"low": 0.15, "moderate": 0.4, "high": 0.65, "critical": 0.85}[true_risk]
        
        # Vision
        if true_risk in ("high", "critical"):
            vision_class = rng.choice(["leaf_blast", "bacterial_blight", "brown_spot", "rust"])
            vision_prob = np.clip(base_risk + rng.normal(0, 0.1), 0.3, 0.99)
        else:
            vision_class = "healthy" if rng.random() > 0.2 else rng.choice(disease_classes[1:])
            vision_prob = np.clip(1 - base_risk + rng.normal(0, 0.1), 0.5, 0.99) if vision_class == "healthy" else np.clip(base_risk * 0.5 + rng.normal(0, 0.1), 0.1, 0.6)
        
        # Weather
        if true_risk in ("high", "critical"):
            temp = rng.normal(36, 3)
            humidity = rng.normal(85, 8)
            rainfall = rng.choice([rng.normal(120, 30), rng.normal(2, 1)])
        else:
            temp = rng.normal(27, 3)
            humidity = rng.normal(60, 10)
            rainfall = rng.normal(40, 15)
        
        weather = {
            "avg_temp_c": round(float(temp), 1),
            "humidity_pct": round(float(np.clip(humidity, 20, 100)), 1),
            "rainfall_mm": round(float(max(0, rainfall)), 1),
            "heat_stress_days": int(max(0, rng.normal(3 if true_risk in ("high", "critical") else 1, 2))),
        }
        
        # Soil
        if true_risk in ("high", "critical"):
            moisture = rng.normal(18, 8)
            ph = rng.choice([rng.normal(4.8, 0.3), rng.normal(8.5, 0.3)])
            nitrogen = rng.normal(0.6, 0.2)
        else:
            moisture = rng.normal(40, 10)
            ph = rng.normal(6.5, 0.5)
            nitrogen = rng.normal(1.5, 0.4)
        
        soil = {
            "moisture_pct": round(float(np.clip(moisture, 5, 70)), 1),
            "ph": round(float(np.clip(ph, 4.0, 9.0)), 1),
            "nitrogen_g_kg": round(float(max(0.1, nitrogen)), 2),
        }
        
        # Satellite
        if true_risk in ("high", "critical"):
            ndvi = np.clip(rng.normal(0.25, 0.1), 0.05, 0.5)
        else:
            ndvi = np.clip(rng.normal(0.65, 0.1), 0.3, 0.95)
        
        satellite = {
            "ndvi_mean": round(float(ndvi), 3),
        }
        
        scenarios.append({
            "id": i,
            "true_risk_level": true_risk,
            "true_risk_score": round(float(base_risk), 3),
            "vision_prob": round(float(vision_prob), 4),
            "vision_class": vision_class,
            "weather": weather,
            "soil": soil,
            "satellite": satellite,
        })
    
    return scenarios


def run_ablation_study(n_scenarios: int = 200, seed: int = 42) -> Dict:
    """
    Run the full ablation study comparing 4 model configurations.
    
    Returns:
        Dictionary with per-model metrics and summary.
    """
    print("[Ablation] Generating scenarios...")
    scenarios = generate_ablation_scenarios(n_scenarios, seed)
    
    fusion = MultimodalRiskFusion()
    
    configs = {
        "A_weather_only": {"use_weather": True, "use_soil": False, "use_satellite": False, "use_vision": False},
        "B_weather_soil": {"use_weather": True, "use_soil": True, "use_satellite": False, "use_vision": False},
        "C_weather_soil_ndvi": {"use_weather": True, "use_soil": True, "use_satellite": True, "use_vision": False},
        "D_full_multimodal": {"use_weather": True, "use_soil": True, "use_satellite": True, "use_vision": True},
    }
    
    results = {}
    all_csv_rows = []
    
    for config_name, use_flags in configs.items():
        print(f"\n[Ablation] Evaluating {config_name}...")
        
        pred_scores = []
        pred_levels = []
        true_scores = []
        true_levels = []
        
        for sc in scenarios:
            kwargs = {}
            if use_flags["use_vision"]:
                kwargs["vision_prob"] = sc["vision_prob"]
                kwargs["vision_class"] = sc["vision_class"]
            if use_flags["use_weather"]:
                kwargs["weather_data"] = sc["weather"]
            if use_flags["use_soil"]:
                kwargs["soil_data"] = sc["soil"]
            if use_flags["use_satellite"]:
                kwargs["satellite_data"] = sc["satellite"]
            
            result = fusion.compute_risk(**kwargs)
            
            pred_scores.append(result["fused_risk_score"])
            pred_levels.append(result["risk_level"])
            true_scores.append(sc["true_risk_score"])
            true_levels.append(sc["true_risk_level"])
            
            all_csv_rows.append({
                "scenario_id": sc["id"],
                "config": config_name,
                "true_risk_score": sc["true_risk_score"],
                "true_risk_level": sc["true_risk_level"],
                "pred_risk_score": result["fused_risk_score"],
                "pred_risk_level": result["risk_level"],
            })
        
        pred_scores = np.array(pred_scores)
        true_scores = np.array(true_scores)
        
        # Metrics
        mae = float(np.mean(np.abs(pred_scores - true_scores)))
        level_agreement = float(np.mean([1 if p == t else 0 for p, t in zip(pred_levels, true_levels)]))
        spearman_r, spearman_p = stats.spearmanr(true_scores, pred_scores)
        
        results[config_name] = {
            "mae": round(mae, 4),
            "level_agreement": round(level_agreement, 4),
            "spearman_r": round(float(spearman_r), 4),
            "spearman_p": round(float(spearman_p), 6),
            "n_scenarios": n_scenarios,
            "modalities": [k.replace("use_", "") for k, v in use_flags.items() if v],
        }
        
        print(f"  MAE: {mae:.4f}, Level Agreement: {level_agreement:.2%}, "
              f"Spearman ρ: {spearman_r:.4f}")
    
    # ── Save results ──────────────────────────────────────────
    # JSON report
    report = {
        "ablation_study": results,
        "summary": {
            "best_model": min(results, key=lambda k: results[k]["mae"]),
            "best_mae": min(r["mae"] for r in results.values()),
            "improvement_full_vs_weather": round(
                results["A_weather_only"]["mae"] - results["D_full_multimodal"]["mae"], 4
            ),
        },
    }
    
    json_path = os.path.join(REPORTS_DIR, "ablation_results.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    
    # CSV report
    csv_path = os.path.join(REPORTS_DIR, "ablation_results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_csv_rows[0].keys())
        writer.writeheader()
        writer.writerows(all_csv_rows)
    
    print(f"\n[Ablation] JSON report: {json_path}")
    print(f"[Ablation] CSV report: {csv_path}")
    print(f"[Ablation] Best model: {report['summary']['best_model']} (MAE={report['summary']['best_mae']:.4f})")
    
    return report


if __name__ == "__main__":
    run_ablation_study()
