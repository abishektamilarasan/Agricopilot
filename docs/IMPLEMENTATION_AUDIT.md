# Implementation Audit: AgriCopilot

**Date:** September 2026  
**Auditor:** Antigravity AI Engine  
**Project:** AgriCopilot — Multimodal Agricultural Decision-Support System  

---

## 1. Executive Summary & Existing Architecture

AgriCopilot is designed as a multimodal AI decision-intelligence assistant for precision agriculture. The architecture connects environmental sensor APIs, satellite proxies, agronomic parameters, rule-based forecasters, and a local RAG pipeline to provide agricultural recommendations.

### High-Level System Architecture

```text
               ┌────────────────────────────────────────────────────────┐
               │              Next.js 14 Web Frontend                  │
               │  • / (Main Dashboard)    • /crop-doctor (Vision)       │
               │  • /risk-dashboard       • /chat (RAG Copilot)         │
               │  • /analytics                                          │
               └──────────────────────────┬─────────────────────────────┘
                                          │ HTTP REST / JSON
                                          ▼
               ┌────────────────────────────────────────────────────────┐
               │                  FastAPI Backend                       │
               │               (backend/main.py:8000)                   │
               └──────────┬───────────────────────────────┬─────────────┘
                          │                               │
        Data Fetching & Alignment             AI Engines & Forecasters
                          ▼                               ▼
       ┌───────────────────────────────┐ ┌─────────────────────────────┐
       │ Data Sources & ETL            │ │ Forecasting & Fusion        │
       │ • Open-Meteo (Weather/ET0)    │ │ • YieldForecaster (Linear)  │
       │ • NASA POWER (Solar/Agroclim) │ │ • WaterStress (Mass balance)│
       │ • SoilGrids 2.0 (ISRIC Soil)  │ │ • DiseaseRisk (Weighted sum)│
       │ • Agromonitoring (NDVI)       │ │ • FertilizerRecommender(Eq) │
       │ • Agmarknet (Market prices)   │ │ • Dempster-Shafer Fusion    │
       │ • TNAU Agritech (Costs/Priors)│ │ • DecisionFusionEngine      │
       └───────────────────────────────┘ └──────────────┬──────────────┘
                                                        │ Context Injection
                                                        ▼
                                         ┌─────────────────────────────┐
                                         │ Local Ollama LLM + ChromaDB │
                                         │ • Mistral / Llama3          │
                                         │ • nomic-embed-text          │
                                         └─────────────────────────────┘
```

---

## 2. Existing Models & Current Decision Logic

Our audit of `backend/forecasting.py`, `backend/analysis_engine.py`, `backend/decision_fusion.py`, and `backend/api/vision_routes.py` revealed:

| Component | Current Implementation | Type / Logic | Limitations |
| :--- | :--- | :--- | :--- |
| **Plant Disease** | `backend/api/vision_routes.py`<br>`backend/api/ml_routes.py` | Remote HuggingFace API call (`linkan/plant-disease-classification`) with hardcoded mock fallback | Fails offline, no local weights, no Grad-CAM attention maps, no top-$k$ distribution, mock returns fixed Northern Leaf Blight |
| **Yield Prediction** | `YieldForecaster` in `forecasting.py` | Deterministic equation:<br>$\text{Yield} = \mu \times \text{drought\_factor} \times \text{pH\_factor} \times \text{irrigation\_factor} \times (1 + \frac{\text{GDD}}{100})$ | Linear heuristic; lacks empirical regression weights, non-linear interactions, and feature importance (SHAP) |
| **Water Stress & Forecasting** | `WaterStressForecaster` in `forecasting.py` | 1-step balance: $\text{deficit} = \max(\text{ET}_0 - \text{Rainfall}, 0)$ | No time-series recurrence, no sequence learning (LSTM), no multi-day forecast horizon |
| **Disease Risk** | `DiseaseRiskForecaster` in `forecasting.py` | Fixed weighted formula:<br>$0.40 T + 0.35 RH + 0.15 P + 0.10 \text{Hist}$ | Arbitrary weights; does not ingest visual image probabilities or multimodal feature interactions |
| **Fertilizer Recommendation** | `FertilizerRecommender` in `forecasting.py` | Crop nutrient uptake minus soil N plus constant safety margin (+20 kg/ha) | Pure mass-balance rule; static, non-adaptive to regional yield targets |
| **Uncertainty & Confidence** | `backend/agents/confidence.py` & `explainability.py` | Dempster-Shafer BPA intervals $[Bel, Pl]$ and data completeness heuristics | Lacks statistical conformal prediction intervals ($1-\alpha$ coverage bounds) for numerical outputs |
| **Decision Fusion** | `DecisionFusionEngine` in `decision_fusion.py` | Threshold-based conditional rules (`stress > 0.6`, `risk > 0.7`) | Brittle if/else logic rather than hybrid probabilistic decision fusion |

---

## 3. Existing Data Sources & Integrations

| Data Source | Provider | Status | Integration File |
| :--- | :--- | :--- | :--- |
| **Weather** | Open-Meteo API | Working (Free, No key needed) | `backend/data_sources/weather.py` |
| **Agroclimatology** | NASA POWER API | Working (Free) | `backend/data_sources/nasa_power.py` |
| **Soil Properties** | ISRIC SoilGrids 2.0 | Working (Free REST API) + TN fallback | `backend/data_sources/soil.py`, `tn_soil_map.py` |
| **Satellite / NDVI** | Agromonitoring | Integrated (Requires API key, graceful fallback) | `backend/data_sources/satellite.py` |
| **Market Prices** | Agmarknet (data.gov.in) | Integrated (Graceful fallback to `unavailable`) | `backend/data_sources/market.py` |
| **Cultivation Costs** | TNAU Agritech scraper | Working for Rice, Maize, Groundnut, Tomato, Banana | `backend/data_sources/costs.py` |
| **Historical Yield Prior** | Local JSON | Curated baseline for Tamil Nadu crops | `backend/data_sources/datasets/india_yields.json` |

---

## 4. Existing Database & Vector Store

* **Vector Database:** ChromaDB `v0.6.3` stored in `./chroma_db`.
* **Embedding Model:** Ollama `nomic-embed-text`.
* **Knowledge Corpus:** Ingested in `backend/rag/ingestion.py` covering crop guidelines (Rice, Maize, Millets, Sugarcane, Cotton, Tomato, etc.) and Tamil Nadu soil types.

---

## 5. Existing Frontend Features (Next.js 14)

1. **Dashboard (`/`):** Full field analysis, coordinate picker, interactive map, summary cards, weather forecast, soil profile, RAG recommendations.
2. **Explainable AI Risk Dashboard (`/risk-dashboard`):** 6-dimension risk heatmap (Drought, Flood, Heat, Pest, Soil Degradation, Market), Dempster-Shafer belief/plausibility intervals, Step-by-step chain-of-thought audit trail, Field Health Score (0-100).
3. **Crop Doctor (`/crop-doctor`):** Leaf image upload drag-and-drop, calls `/api/diagnose-disease`.
4. **Chat Copilot (`/chat`):** Interactive Q&A connected to RAG and web search.
5. **Analytics (`/analytics`):** Historical tracking and charts.

---

## 6. Current Limitations & Missing Components

1. **No Real Local Computer Vision Model:** Currently relies on external Hugging Face inference or mock fallbacks; no local PyTorch EfficientNetV2, no Grad-CAM attention maps.
2. **Deterministic Yield Heuristic:** Yield prediction is an uncalibrated multiplier rather than a trained ML model (Linear Regression, Random Forest, XGBoost).
3. **No Multi-Horizon Sequence Model:** Water stress forecasting lacks temporal memory (LSTM / GRU) across multi-day horizons (1, 3, 7, 14 days).
4. **No Multimodal Vision + Environmental Risk Fusion:** Leaf images and weather/soil contexts are evaluated in isolation rather than fused into a multimodal disease risk model.
5. **No Conformal Prediction:** Uncertainty is limited to subjective bounds ($\pm 15\%$) rather than rigorous non-parametric conformal prediction intervals ($[y_{lower}, y_{upper}]$ with $90\%$ empirical coverage).
6. **No Automated Ablation & Benchmarking Suite:** No automated experiments comparing Rule-Based Baseline vs. Classical ML vs. Deep Learning vs. Multimodal Fusion.
7. **Frontend Missing Model Insights & Performance Hub:** Frontend lacks SHAP feature importance charts, Grad-CAM visual heatmaps, prediction intervals, and offline experimental metrics tables.

---

## 7. Recommended Components & Files to Modify/Add

### New Files to Create:
* `ml/disease/`: EfficientNetV2 dataset loader, training, validation, Grad-CAM, inference engine.
* `ml/yield/`: Linear Regression, Random Forest, and XGBoost yield prediction pipelines + conformal prediction.
* `ml/timeseries/`: LSTM multi-horizon soil moisture & water stress forecasting model.
* `ml/fusion/`: Multimodal disease risk & hybrid decision fusion engine.
* `ml/explainability/`: SHAP explainer for tabular models + Grad-CAM generator for leaf images.
* `ml/uncertainty/`: Split conformal prediction framework with coverage diagnostics.
* `scripts/train_all.py`: End-to-end reproducible experiment runner.
* `reports/`: `disease_metrics.json`, `yield_metrics.json`, `ablation_results.csv`, `ablation_results.json`, and visual figures.
* `docs/`: `ARCHITECTURE.md`, `MODEL_CARD.md`, `EXPERIMENTS.md`, `DATASETS.md`, `LIMITATIONS.md`.

### Existing Files to Modify:
* `backend/requirements.txt`: Update dependencies to include scikit-learn, xgboost, shap, torch, torchvision.
* `backend/main.py`: Mount new model endpoints (`/api/disease/predict`, `/api/yield/predict`, `/api/water/forecast`, `/api/fusion/analyze`, `/api/experiments/results`).
* `backend/forecasting.py`: Integrate trained models alongside existing baseline forecasters.
* `backend/decision_fusion.py`: Upgrade to hybrid learned + constraint-based decision engine.
* `backend/api/vision_routes.py` & `ml_routes.py`: Wire real local inference and Grad-CAM outputs.
* `frontend/app/crop-doctor/page.js`: Add Grad-CAM attention overlay, top-k class distribution, multimodal risk warning.
* `frontend/app/components/`: Add Model Performance comparison table & SHAP feature contribution charts.
