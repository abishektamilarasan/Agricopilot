# 🌾 AgriCopilot: Agricultural AI Decision Intelligence

**AgriCopilot** is a multimodal AI Copilot for farmers and agricultural officers—combining satellite-free data sources with machine learning to provide actionable, interpretable recommendations for crop management.

**Instead of:** "Our CNN achieved 96% accuracy on crop disease detection."  
**We deliver:** "Yield will decrease by ~12% due to expected rainfall. Delay irrigation by 3 days. Nitrogen deficiency is likely. Confidence: 78%"

---

## 🎯 Why AgriCopilot?

### The Problem
Most published agricultural AI systems solve **one** problem:
- Crop disease detection
- Yield prediction
- Irrigation scheduling
- Fertilizer recommendation

But farmers need **integrated reasoning** across all of them.

### Our Solution
A **multimodal decision-support system** integrating:
- 🌡️ **Weather forecasts** (temperature, humidity, rainfall, solar radiation)
- 🌍 **Soil properties** (texture, pH, nutrients, water capacity)
- 💰 **Market prices** (commodity trends, seasonality)
- 📊 **Historical data** (past yields, disease occurrence, practices)
- 🗣️ **Farmer queries** (contextualized via RAG + LLMs)

**Outputs:** Joint predictions + economic tradeoffs + confidence scores + reasoning chains.

---

## 🏗️ Architecture

```
Data Ingestion (ETL)
    ├── Weather (Open-Meteo, NASA Power)
    ├── Soil (SoilGrids)
    ├── Market (FAO STAT, local APIs)
    └── Historical (TNAU, farmer input)
    
         ↓
    
Aligned DataFrames
    (standardized spatiotemporal keys)
    
         ↓
    
Time-Series Forecasters
    ├── YieldForecaster (soil + weather → kg/ha)
    ├── WaterStressForecaster (water balance → stress index)
    ├── DiseaseRiskForecaster (T + RH + rainfall → risk)
    └── FertilizerRecommender (soil + yield → N, P, K)
    
         ↓
    
Decision Fusion Engine
    (integrate all forecasts + business rules)
    
         ↓
    
Agricultural Decision
    ├── Irrigation schedule (when, how much)
    ├── Fertilizer plan (amounts, timing, split)
    ├── Disease management (preventive measures)
    ├── Harvest estimate (date, yield, profit)
    └── Confidence scores & explanations
    
         ↓
    
Chat Interface (Ollama + RAG)
    (Q&A with context, refinement loop)
```

---

## 📦 Project Structure

```
agricopilot/
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Configuration & crop parameters
│   ├── requirements.txt         # Python dependencies
│   ├── data_pipeline.py         # ETL + aligned data structures
│   ├── forecasting.py           # Time-series forecasters
│   ├── decision_fusion.py       # Decision engine + explainability
│   ├── agents/
│   │   ├── copilot.py          # LLM-based reasoning & RAG
│   │   ├── prompts.py          # LLM prompt templates
│   │   └── confidence.py       # Confidence calibration
│   ├── data_sources/
│   │   ├── weather.py          # Open-Meteo integration
│   │   ├── nasa_power.py       # NASA POWER API
│   │   ├── soil.py             # SoilGrids integration
│   │   └── market.py           # FAO STAT integration
│   ├── rag/
│   │   ├── ingestion.py        # Knowledge base ingestion
│   │   └── knowledge_base.py   # RAG queries
│   ├── api/
│   │   └── ml_routes.py        # ML prediction endpoints
│   ├── tests/
│   │   └── test_pipeline.py    # Unit tests
│   └── chroma_db/              # Vector store (persisted)
│
├── frontend/
│   ├── app/
│   │   ├── page.js             # Home
│   │   ├── chat/page.js        # Chat interface
│   │   ├── crop-doctor/page.js # Diagnosis UI
│   │   ├── analytics/page.js   # Results dashboard
│   │   └── components/
│   │       └── LocationPicker.js
│   ├── package.json
│   └── next.config.mjs
│
├── Dockerfile.backend          # Backend container
├── Dockerfile.frontend         # Frontend container
├── docker-compose.yml          # Full stack orchestration
├── .env.example                # Environment template
├── .gitignore                  # Repo cleanliness
└── README.md                   # This file
```

---

## 🚀 Quick Start

### Prerequisites
- **Docker & Docker Compose** (recommended)
- OR: Python 3.11+, Node.js 20+, Ollama

### Option 1: Docker (Recommended)

```bash
# Clone and setup
git clone <your-repo>
cd agricopilot

# Create .env (copy from .env.example)
cp .env.example .env

# Start all services
docker-compose up -d

# Pull LLM models into Ollama container
docker exec agricopilot-ollama ollama pull mistral
docker exec agricopilot-ollama ollama pull nomic-embed-text

# Access services
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# Ollama:    http://localhost:11434
# Chroma:    http://localhost:8001
```

### Option 2: Local Development

#### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Ollama (in another terminal)
ollama serve

# Pull models
ollama pull mistral
ollama pull nomic-embed-text

# Run backend
uvicorn main:app --reload
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# Open http://localhost:3000
```

---

## 📡 API Endpoints

### Analysis Endpoint
```bash
POST /api/analyze
Content-Type: application/json

{
  "latitude": 20.5937,
  "longitude": 78.9629,
  "crop": "rice",
  "planting_date": "2024-06-15",
  "days_ahead": 30
}

# Returns:
{
  "yield_forecast_kg_ha": 3200,
  "yield_ci_lower": 2800,
  "yield_ci_upper": 3600,
  "irrigation_total_mm": 120,
  "fertilizer_n_kg_ha": 85,
  "disease_risks": ["Blast", "Brown spot"],
  "expected_profit_per_ha": 28000,
  "overall_confidence": 0.72,
  "explanations": {...}
}
```

### Chat Endpoint (RAG + LLM)
```bash
POST /api/chat
Content-Type: application/json

{
  "latitude": 20.5937,
  "longitude": 78.9629,
  "crop": "rice",
  "query": "Should I irrigate now given recent rainfall?"
}

# Returns:
{
  "response": "Based on soil moisture simulations and ...",
  "confidence": 0.78,
  "sources": ["water_stress_forecast", "market_analysis", ...]
}
```

---

## 🧪 Testing

```bash
# Run unit tests
cd backend
pip install pytest
pytest tests/ -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=. --cov-report=html

# Open htmlcov/index.html
```

---

## 📊 Data Sources & APIs

All **free** and **no API keys required**:

| Data Source | API | Fields |
|---|---|---|
| **Weather** | Open-Meteo | Temp, humidity, precipitation, solar radiation |
| **Soil** | SoilGrids (ISRIC) | Clay%, sand%, pH, organic matter, nutrients, AWC |
| **Market** | FAO STAT | Commodity prices, trends, seasonality |
| **Climate** | NASA POWER | Historical daily data, radiation, evapotranspiration |

---

## 🤖 LLM & RAG

- **LLM:** Ollama (local) with Mistral or other models
- **Embeddings:** Nomic Embed Text (open-source)
- **Vector Store:** ChromaDB (persisted)
- **Knowledge Base:** TNAU Agritech, FAO docs, crop parameters

**Inference:** Entirely local; no external LLM API calls.

---

## 🔍 Explainability & Confidence

Each recommendation includes:
1. **Point estimate** (e.g., yield = 3200 kg/ha)
2. **Confidence interval** (CI 95%; lower/upper bounds)
3. **Confidence score** (0–1; based on data quality & model agreement)
4. **Reasoning chain** (how each input contributed to the output)
5. **Limitations** (missing data, model assumptions)

Example:
```json
{
  "variable": "water_stress_index",
  "point_estimate": 0.62,
  "lower_ci": 0.47,
  "upper_ci": 0.77,
  "confidence": 0.68,
  "explanation": "Water balance: Rainfall=15mm, PET=4.2mm, Drainage=0.8mm → Soil moisture stressed (0.62/1.0). Confidence lower due to no soil sensor data."
}
```

---

## 📈 Evaluation Metrics

- **Yield Forecast RMSE:** Error vs. ground truth (kg/ha)
- **Water Stress Correlation:** Agreement with soil moisture sensors
- **Disease Detection Precision/Recall:** vs. farmer observations
- **Farmer Satisfaction:** Usability, actionability of recommendations
- **Economic Value:** Profit increase vs. baseline practices

---

## 🔐 Security & Privacy

- ✅ **No satellite imagery** (cost, privacy concerns)
- ✅ **Local LLM inference** (no data sent to OpenAI, Cohere, etc.)
- ✅ **Environment variables** for all secrets (.env.example template)
- ✅ **Input validation** on all ETL pipelines
- ⚠️ **TODO:** User authentication, encrypted storage for field data

---

## 🛠️ Development Roadmap

- [ ] Add soil moisture sensor ingestion (RTK-GPS + IoT)
- [ ] Integrate farmer practice history (app-based logging)
- [ ] Multimodal vision: farmer/drone images + lightweight segmentation models
- [ ] Improve disease detection: historical geospatial patterns
- [ ] Economic modules: cost-benefit analysis for interventions
- [ ] Mobile app (React Native) for offline use
- [ ] Crowdsourced validation loop (feedback from farmers)

---

## 📚 Research & Novelty

**AgriCopilot** combines:
- **Multimodal Transformers** (weather + soil + market time-series)
- **Vision-Language Models** (for optional image inputs)
- **Time-Series Forecasting** (LSTM/Transformer-based)
- **Retrieval-Augmented Generation** (RAG for contextual Q&A)
- **LLM-based Reasoning** (chain-of-thought explanations)
- **Explainable AI** (confidence scores, feature importance)
- **AI Agents** (multi-step decision loops)

**Research Novelty:**
- First open-source agricultural AI Copilot integrating heterogeneous data
- Joint optimization of yield, irrigation, fertilizer, and profitability
- Uncertainty quantification and calibrated confidence scores
- Reasoning chains for farmer trust and debugging

---

## 🤝 Contributing

1. Fork and branch (`git checkout -b feature/your-feature`)
2. Make changes; add tests
3. Run `pytest`, `npm run lint`
4. Submit PR with description

---

## 📄 License

MIT License. See `LICENSE` file.

---

## 🙋 Contact & Support

- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
- **Email:** agricopilot@example.com

---

**Built for farmers, by ML engineers. Let's end agricultural waste. 🌾**
