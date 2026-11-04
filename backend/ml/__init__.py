"""
AgriCopilot ML Module
Real trained ML/CV models for precision agriculture decision support.

Sub-packages:
    disease   — EfficientNetV2 plant disease classification + Grad-CAM
    yield_pred — Tabular yield prediction (LR, RF, XGBoost) + SHAP + Conformal
    fusion    — Multimodal disease-risk fusion + ablation study
"""

import os
import torch

# ── Device selection ──────────────────────────────────────────
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ── Paths ─────────────────────────────────────────────────────
ML_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(ML_ROOT)
REPORTS_DIR = os.path.join(BACKEND_ROOT, "reports")
CHECKPOINTS_DIR = os.path.join(ML_ROOT, "checkpoints")
DATA_DIR = os.path.join(ML_ROOT, "data")

for _d in (REPORTS_DIR, CHECKPOINTS_DIR, DATA_DIR):
    os.makedirs(_d, exist_ok=True)

__all__ = ["DEVICE", "ML_ROOT", "BACKEND_ROOT", "REPORTS_DIR", "CHECKPOINTS_DIR", "DATA_DIR"]
