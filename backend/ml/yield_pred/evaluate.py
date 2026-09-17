"""
Yield Prediction Evaluation Module

Generates evaluation plots and detailed metrics reports:
  - Actual vs Predicted scatter plots
  - Residual distribution plots  
  - Feature importance bar charts
  - Model comparison tables
"""

import json
import os
from typing import Dict, Optional

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

from ml import REPORTS_DIR
from ml.yield_pred.dataset import ALL_FEATURES, get_train_val_test, get_feature_matrix


def generate_evaluation_plots(
    models_dict: Dict,
    scalers_dict: Dict,
    n_samples: int = 2000,
    seed: int = 42,
) -> Dict[str, str]:
    """
    Generate evaluation plots for all trained models.
    
    Args:
        models_dict: {model_name: trained_model}
        scalers_dict: {model_name: StandardScaler or None}
        
    Returns:
        Dictionary of {plot_name: file_path}
    """
    figures_dir = os.path.join(REPORTS_DIR, "figures")
    os.makedirs(figures_dir, exist_ok=True)
    
    # Get test data
    _, _, test_df = get_train_val_test(n_samples=n_samples, seed=seed)
    X_test, y_test = get_feature_matrix(test_df)
    
    plot_paths = {}
    
    # ── 1. Actual vs Predicted (per model) ────────────────────
    fig, axes = plt.subplots(1, len(models_dict), figsize=(6 * len(models_dict), 5))
    if len(models_dict) == 1:
        axes = [axes]
    
    for ax, (name, model) in zip(axes, models_dict.items()):
        scaler = scalers_dict.get(name)
        X = scaler.transform(X_test) if scaler else X_test
        y_pred = model.predict(X)
        
        ax.scatter(y_test, y_pred, alpha=0.3, s=10, color="#4CAF50")
        
        # Perfect prediction line
        lims = [min(y_test.min(), y_pred.min()), max(y_test.max(), y_pred.max())]
        ax.plot(lims, lims, "r--", linewidth=1.5, label="Perfect")
        
        ax.set_xlabel("Actual Yield (tons/ha)")
        ax.set_ylabel("Predicted Yield (tons/ha)")
        ax.set_title(f"{name.replace('_', ' ').title()}")
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.suptitle("Actual vs Predicted Yield", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(figures_dir, "actual_vs_predicted.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    plot_paths["actual_vs_predicted"] = path
    
    # ── 2. Residual Distribution ──────────────────────────────
    fig, axes = plt.subplots(1, len(models_dict), figsize=(6 * len(models_dict), 4))
    if len(models_dict) == 1:
        axes = [axes]
    
    for ax, (name, model) in zip(axes, models_dict.items()):
        scaler = scalers_dict.get(name)
        X = scaler.transform(X_test) if scaler else X_test
        y_pred = model.predict(X)
        residuals = y_test - y_pred
        
        sns.histplot(residuals, bins=40, kde=True, ax=ax, color="#2196F3")
        ax.axvline(0, color="red", linestyle="--", linewidth=1.5)
        ax.set_xlabel("Residual (Actual - Predicted)")
        ax.set_title(f"{name.replace('_', ' ').title()}")
        ax.grid(True, alpha=0.3)
    
    plt.suptitle("Residual Distribution", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(figures_dir, "residual_distribution.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    plot_paths["residual_distribution"] = path
    
    # ── 3. Feature Importance (tree models only) ──────────────
    for name, model in models_dict.items():
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            indices = np.argsort(importances)[::-1][:15]  # Top 15
            
            fig, ax = plt.subplots(figsize=(10, 6))
            colors = sns.color_palette("viridis", len(indices))
            ax.barh(
                [ALL_FEATURES[i] for i in indices][::-1],
                importances[indices][::-1],
                color=colors,
            )
            ax.set_xlabel("Feature Importance")
            ax.set_title(f"Top 15 Features — {name.replace('_', ' ').title()}")
            ax.grid(True, alpha=0.3, axis="x")
            plt.tight_layout()
            path = os.path.join(figures_dir, f"feature_importance_{name}.png")
            plt.savefig(path, dpi=150, bbox_inches="tight")
            plt.close()
            plot_paths[f"feature_importance_{name}"] = path
    
    print(f"[YieldEval] Plots saved to {figures_dir}")
    return plot_paths


def generate_model_comparison_table(metrics: Dict) -> str:
    """
    Generate a markdown table comparing model performance.
    """
    lines = [
        "| Model | Train MAE | Train R² | Val MAE | Val R² | Test MAE | Test RMSE | Test R² |",
        "|-------|-----------|----------|---------|--------|----------|-----------|---------|",
    ]
    
    for name, m in metrics.items():
        lines.append(
            f"| {name.replace('_', ' ').title()} | "
            f"{m['train']['mae']:.4f} | {m['train']['r2']:.4f} | "
            f"{m['val']['mae']:.4f} | {m['val']['r2']:.4f} | "
            f"{m['test']['mae']:.4f} | {m['test']['rmse']:.4f} | {m['test']['r2']:.4f} |"
        )
    
    return "\n".join(lines)
