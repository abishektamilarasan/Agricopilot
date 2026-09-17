# Model Card: AgriCopilot Multimodal Engine

## Model Details
*   **Name:** AgriCopilot Fusion Engine (v1.0)
*   **Type:** Hybrid Multimodal (EfficientNetV2 + XGBoost + LSTM + Bayesian Fusion)
*   **Date:** September 2026
*   **License:** MIT

## Intended Use
*   **Primary Use Case:** Providing explainable, data-driven decision support for precision agriculture, specifically for crop disease diagnosis, yield prediction, and water-stress forecasting.
*   **Users:** Farmers, agricultural extension officers, and agronomists.
*   **Out of Scope:** Automated actuation of irrigation systems without human-in-the-loop verification.

## Training Data
*   **Disease Model:** Fine-tuned on synthetic datasets representing key foliar diseases.
*   **Yield Model:** Trained on synthetic tabular datasets simulating regional climate patterns, soil profiles, and historical yields.
*   **Forecasting Model:** Trained on time-series meteorological simulations.

## Performance & Metrics
*   **Yield Prediction:** Mean Absolute Error (MAE) of 2.26 tons/ha with an R² of 0.97.
*   **Water Stress Forecasting:** Demonstrates positive skill (+0.35) over a 14-day horizon compared to a naive persistence baseline.
*   **Risk Assessment:** The full multimodal fusion model achieves a Mean Absolute Error of 0.17 on continuous risk scoring.

## Limitations & Bias
*   The models are currently trained on synthetic data distributions designed for prototyping and conceptual validation.
*   Performance on real-world edge cases (e.g., rare diseases, extreme unprecedented weather anomalies) is not validated.
*   Recommendations should be cross-referenced with local agronomic expertise.

## Ethical Considerations
*   **Transparency:** Implemented SHAP (Shapley Additive exPlanations) and Grad-CAM to ensure the system's decisions are interpretable.
*   **Uncertainty:** Uses Conformal Prediction to output calibrated confidence intervals rather than overconfident point estimates, preventing misleading advice during high-uncertainty events.
