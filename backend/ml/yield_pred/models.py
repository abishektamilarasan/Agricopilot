"""
Yield Prediction Models

Provides three model types for crop yield prediction:
  1. Linear Regression (baseline)
  2. Random Forest Regressor
  3. XGBoost Regressor

Each model is wrapped in a consistent API for training, prediction,
SHAP explanation, and conformal prediction intervals.
"""

import json
import os
import pickle
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

from ml import CHECKPOINTS_DIR, REPORTS_DIR
from ml.yield_pred.dataset import (
    ALL_FEATURES, TARGET, generate_synthetic_yield_data,
    get_train_val_test, get_feature_matrix,
)


class YieldModelRegistry:
    """
    Registry of yield prediction models with unified train/predict/explain API.
    """

    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.metrics: Dict[str, Dict] = {}
        self.calibration_residuals: Dict[str, np.ndarray] = {}
        self._feature_names = ALL_FEATURES

    def train_all(
        self,
        n_samples: int = 2000,
        seed: int = 42,
    ) -> Dict[str, Dict]:
        """
        Train all three model types and evaluate.
        
        Returns:
            Dictionary of metrics for each model.
        """
        print("[YieldModels] Generating dataset...")
        train_df, val_df, test_df = get_train_val_test(n_samples=n_samples, seed=seed)
        
        X_train, y_train = get_feature_matrix(train_df)
        X_val, y_val = get_feature_matrix(val_df)
        X_test, y_test = get_feature_matrix(test_df)
        
        # Standardize features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        X_test_scaled = scaler.transform(X_test)
        
        model_configs = {
            "linear_regression": {
                "model": LinearRegression(),
                "uses_scaling": True,
            },
            "random_forest": {
                "model": RandomForestRegressor(
                    n_estimators=200,
                    max_depth=15,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    random_state=seed,
                    n_jobs=-1,
                ),
                "uses_scaling": False,
            },
        }
        
        if HAS_XGBOOST:
            model_configs["xgboost"] = {
                "model": xgb.XGBRegressor(
                    n_estimators=300,
                    max_depth=8,
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    reg_alpha=0.1,
                    reg_lambda=1.0,
                    random_state=seed,
                    tree_method="hist",
                    device="cuda" if self._has_cuda() else "cpu",
                ),
                "uses_scaling": False,
            }
        
        all_metrics = {}
        
        for name, config in model_configs.items():
            print(f"\n[YieldModels] Training {name}...")
            t0 = time.time()
            
            model = config["model"]
            uses_scaling = config["uses_scaling"]
            
            X_tr = X_train_scaled if uses_scaling else X_train
            X_v = X_val_scaled if uses_scaling else X_val
            X_te = X_test_scaled if uses_scaling else X_test
            
            # Train
            if name == "xgboost" and HAS_XGBOOST:
                model.fit(X_tr, y_train, eval_set=[(X_v, y_val)], verbose=False)
            else:
                model.fit(X_tr, y_train)
            
            elapsed = time.time() - t0
            
            # Predict
            y_pred_train = model.predict(X_tr)
            y_pred_val = model.predict(X_v)
            y_pred_test = model.predict(X_te)
            
            # Metrics
            metrics = {
                "train": self._compute_metrics(y_train, y_pred_train),
                "val": self._compute_metrics(y_val, y_pred_val),
                "test": self._compute_metrics(y_test, y_pred_test),
                "training_time_s": round(elapsed, 2),
            }
            
            # Compute calibration residuals for conformal prediction
            cal_residuals = np.abs(y_val - y_pred_val)
            self.calibration_residuals[name] = cal_residuals
            
            # Store
            self.models[name] = model
            self.scalers[name] = scaler if uses_scaling else None
            self.metrics[name] = metrics
            all_metrics[name] = metrics
            
            print(f"  {name}: Test MAE={metrics['test']['mae']:.3f}, "
                  f"RMSE={metrics['test']['rmse']:.3f}, R²={metrics['test']['r2']:.4f} "
                  f"({elapsed:.1f}s)")
        
        # Save all models and metrics
        self._save_all()
        
        return all_metrics

    def predict(
        self,
        features: Dict[str, float],
        model_name: str = "xgboost",
        alpha: float = 0.1,
    ) -> Dict:
        """
        Predict yield with conformal interval and optional SHAP explanation.
        
        Args:
            features: Dictionary mapping feature names to values.
            model_name: Which model to use.
            alpha: Significance level for conformal interval (0.1 = 90% coverage).
            
        Returns:
            Dictionary with prediction, interval, and SHAP values.
        """
        if model_name not in self.models:
            # Fallback to whatever is available
            available = list(self.models.keys())
            if not available:
                return {"error": "No trained models available. Call train_all() first."}
            model_name = available[-1]
        
        model = self.models[model_name]
        scaler = self.scalers.get(model_name)
        
        # Build feature vector
        x = np.array([[features.get(f, 0.0) for f in self._feature_names]], dtype=np.float32)
        if scaler:
            x = scaler.transform(x)
        
        # Point prediction
        y_pred = float(model.predict(x)[0])
        
        # Conformal prediction interval
        interval = self._conformal_interval(model_name, y_pred, alpha)
        
        # SHAP explanation
        shap_values = self._compute_shap(model_name, x)
        
        return {
            "predicted_yield_tons_ha": round(y_pred, 3),
            "conformal_interval": {
                "lower": round(interval[0], 3),
                "upper": round(interval[1], 3),
                "coverage": f"{int((1 - alpha) * 100)}%",
                "alpha": alpha,
            },
            "model_used": model_name,
            "shap_explanation": shap_values,
        }

    def _conformal_interval(
        self, model_name: str, y_pred: float, alpha: float = 0.1,
    ) -> Tuple[float, float]:
        """
        Split conformal prediction interval.
        
        Uses calibration residuals from the validation set to compute
        the (1-alpha) quantile of absolute residuals.
        """
        residuals = self.calibration_residuals.get(model_name)
        if residuals is None or len(residuals) == 0:
            # Fallback: ±10% of prediction
            margin = abs(y_pred) * 0.1
            return (y_pred - margin, y_pred + margin)
        
        # Quantile of absolute residuals
        q = np.quantile(residuals, 1 - alpha)
        return (y_pred - q, y_pred + q)

    def _compute_shap(self, model_name: str, x: np.ndarray) -> Optional[Dict]:
        """Compute SHAP values for a single prediction."""
        if not HAS_SHAP:
            return None
        
        model = self.models[model_name]
        
        try:
            if model_name in ("random_forest", "xgboost"):
                explainer = shap.TreeExplainer(model)
                sv = explainer.shap_values(x)
                if isinstance(sv, list):
                    sv = sv[0]
                base_value = float(explainer.expected_value) if np.isscalar(explainer.expected_value) else float(explainer.expected_value[0])
            else:
                # Linear model — use KernelExplainer (slow but works)
                explainer = shap.LinearExplainer(model, x)
                sv = explainer.shap_values(x)
                base_value = float(explainer.expected_value)

            sv = sv.flatten()
            contributions = {}
            for fname, val in zip(self._feature_names, sv):
                contributions[fname] = round(float(val), 4)

            # Sort by absolute contribution
            sorted_contrib = dict(
                sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)
            )

            return {
                "base_value": round(base_value, 4),
                "feature_contributions": sorted_contrib,
                "top_3_features": list(sorted_contrib.keys())[:3],
            }
        except Exception as e:
            return {"error": str(e)}

    def _compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """Compute regression metrics."""
        return {
            "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
            "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
            "r2": round(float(r2_score(y_true, y_pred)), 4),
            "n_samples": int(len(y_true)),
        }

    def _has_cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _save_all(self):
        """Save models, scalers, and metrics to disk."""
        # Save models
        for name, model in self.models.items():
            model_path = os.path.join(CHECKPOINTS_DIR, f"yield_{name}.pkl")
            with open(model_path, "wb") as f:
                pickle.dump(model, f)
        
        # Save scalers
        for name, scaler in self.scalers.items():
            if scaler:
                scaler_path = os.path.join(CHECKPOINTS_DIR, f"yield_{name}_scaler.pkl")
                with open(scaler_path, "wb") as f:
                    pickle.dump(scaler, f)
        
        # Save calibration residuals
        for name, residuals in self.calibration_residuals.items():
            res_path = os.path.join(CHECKPOINTS_DIR, f"yield_{name}_cal_residuals.npy")
            np.save(res_path, residuals)
        
        # Save metrics report
        report_path = os.path.join(REPORTS_DIR, "yield_metrics.json")
        with open(report_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
        print(f"\n[YieldModels] Models saved to {CHECKPOINTS_DIR}")
        print(f"[YieldModels] Metrics saved to {report_path}")

    def load_all(self):
        """Load previously trained models from disk."""
        model_names = ["linear_regression", "random_forest", "xgboost"]
        for name in model_names:
            model_path = os.path.join(CHECKPOINTS_DIR, f"yield_{name}.pkl")
            if os.path.isfile(model_path):
                with open(model_path, "rb") as f:
                    self.models[name] = pickle.load(f)
                
                scaler_path = os.path.join(CHECKPOINTS_DIR, f"yield_{name}_scaler.pkl")
                if os.path.isfile(scaler_path):
                    with open(scaler_path, "rb") as f:
                        self.scalers[name] = pickle.load(f)
                
                res_path = os.path.join(CHECKPOINTS_DIR, f"yield_{name}_cal_residuals.npy")
                if os.path.isfile(res_path):
                    self.calibration_residuals[name] = np.load(res_path)
                
                print(f"[YieldModels] Loaded {name}")
        
        metrics_path = os.path.join(REPORTS_DIR, "yield_metrics.json")
        if os.path.isfile(metrics_path):
            with open(metrics_path) as f:
                self.metrics = json.load(f)


def train_yield_models(**kwargs) -> Dict:
    """Convenience function to train all yield models."""
    registry = YieldModelRegistry()
    return registry.train_all(**kwargs)


if __name__ == "__main__":
    train_yield_models()
