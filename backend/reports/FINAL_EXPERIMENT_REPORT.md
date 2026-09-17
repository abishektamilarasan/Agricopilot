# AgriCopilot Final ML Experiment Report

**Date:** 2026-09-05
**Environment:** PyTorch 2.6, XGBoost 2.1, Scikit-Learn 1.5
**Goal:** Upgrade the rule-based Agricultural Decision Support System into a Multimodal ML System.

## 1. Plant Disease Detection
*   **Model:** `EfficientNetV2-S` (Transfer Learning from ImageNet)
*   **Dataset:** Synthetic images generated with targeted augmentations representing `healthy`, `leaf_blast`, `bacterial_blight`, `brown_spot`, and `rust`.
*   **Architecture:** Modified classifier head with Dropout (0.3).
*   **Explainability:** Integrated `Grad-CAM` hooks on the final convolutional block (`features.7.0`) to provide pixel-level visual heatmaps explaining the model's focus areas.

## 2. Crop Yield Prediction
*   **Dataset:** Synthetic agricultural tabular data simulating non-linear interactions between weather, soil properties, and fertilizer application.
*   **Models Evaluated:**
    *   Linear Regression: MAE=8.77, R²=0.73
    *   Random Forest: MAE=2.57, R²=0.95
    *   **XGBoost (Selected):** MAE=2.26, R²=0.97
*   **Uncertainty Estimation:** Split Conformal Prediction implemented to provide 90% confidence intervals around point predictions.
*   **Explainability:** TreeSHAP implemented to output feature importance.

## 3. Water-Stress Forecasting
*   **Model:** 2-Layer LSTM (hidden_size=64, dropout=0.2)
*   **Forecast Horizons:** 1, 3, 7, and 14 days ahead.
*   **Metrics (Skill Score over Naive Baseline):**
    *   1-day Skill: -0.988 (Naive carries forward yesterday's reading, which is hard to beat day-to-day)
    *   7-day Skill: +0.175
    *   14-day Skill: +0.358 (LSTM significantly outperforms the naive baseline over longer horizons).

## 4. Multimodal Fusion & Ablation Study
The novel `MultimodalRiskFusion` module uses Bayesian-inspired evidence fusion to combine visual disease probabilities, weather stress, soil conditions, and satellite NDVI.

**Ablation Results (MAE vs Ground Truth Risk):**
*   **Weather Only:** MAE = 0.2900 (Level Agreement: 40.0%)
*   **Weather + Soil:** MAE = 0.2675 (Level Agreement: 38.5%)
*   **Weather + Soil + NDVI:** MAE = 0.2367 (Level Agreement: 40.0%)
*   **Full Multimodal (Weather+Soil+NDVI+Vision):** MAE = 0.1712 (Level Agreement: 55.5%)

**Conclusion:** The multimodal approach significantly improves the robustness of agricultural risk assessment compared to single-modality baselines.
