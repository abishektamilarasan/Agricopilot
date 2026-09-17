# 🌾 AgriCopilot — Agricultural AI Decision Intelligence

> A first-of-its-kind multimodal AI copilot that reasons across weather, soil, satellite, market, and climate data to generate interpretable agricultural recommendations with confidence estimates.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-orange)
![Cost](https://img.shields.io/badge/Cost-$0-brightgreen)

## 🎯 What Makes This Different

Most agricultural AI systems solve **one** problem (crop disease detection, yield prediction, etc.). AgriCopilot is the first to **reason across all of them together**:

| Capability | Data Sources | Output |
|---|---|---|
| Yield Forecast | Weather + Soil + NDVI | Yield estimate with confidence |
| Water Stress | Precipitation + ET₀ + Soil Moisture | Irrigation schedule |
| Disease Risk | Temperature + Humidity + Knowledge Base | Risk alert + treatment |
| Fertilizer Need | Soil nutrients + Crop requirements | Application plan |
| Harvest Timing | GDD + Crop phenology + Weather | Optimal harvest window |
| Market Strategy | Price trends + Profitability | Buy/sell/store advice |

**Research framing:**
> *"Our multimodal AI decision-support system integrates heterogeneous agricultural data and generates interpretable recommendations with confidence estimates via a retrieval-augmented LLM agent pipeline."*

## 🏗️ Architecture

```
Satellite/NDVI ──┐
Weather API ─────┤
Soil Data ───────┼──→ FastAPI Backend ──→ RAG Pipeline ──→ Ollama LLM ──→ Recommendations
NASA POWER ──────┤         │                                                    │
Market Data ─────┘         └──→ Confidence Engine ──────────────────────────────┘
                                         │
                                    Next.js Frontend (Dashboard + Chat + Analytics)
```

### Tech Stack (100% Free)

| Layer | Technology |
|---|---|
| LLM | Ollama + Mistral 7B (local, free) |
| Vector DB | ChromaDB (local, free) |
| Backend | FastAPI + Python 3.11+ |
| Frontend | Next.js 15 + React |
| Weather | Open-Meteo API (free, no key) |
| Climate | NASA POWER API (free, no key) |
| Market | FAOSTAT + curated database |
| Soil | SoilGrids + regional fallback DB |
| Vegetation | NDVI simulation engine |

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Ollama** — [Install from ollama.com](https://ollama.com)

### 1. Start Ollama & Pull Model

```bash
# Install Ollama, then:
ollama pull mistral
ollama pull nomic-embed-text
```

### 2. Start the Backend

```bash
cd agricopilot/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

The API will be available at `http://localhost:8000`. Visit `http://localhost:8000/docs` for the interactive Swagger UI.

### 3. Start the Frontend

```bash
cd agricopilot/frontend

# Install dependencies (already done during setup)
npm install

# Run dev server
npm run dev
```

Visit `http://localhost:3000` to see the dashboard.

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/analyze` | POST | Full agricultural analysis |
| `/api/chat` | POST | Conversational copilot |
| `/api/weather/{lat}/{lon}` | GET | Weather data |
| `/api/soil/{lat}/{lon}` | GET | Soil properties |
| `/api/market/{crop}/{country}` | GET | Market data |
| `/api/ndvi/{lat}/{lon}` | GET | Vegetation health |
| `/api/nasa/{lat}/{lon}` | GET | NASA climate data |
| `/api/crops` | GET | Supported crops |
| `/api/health` | GET | System health |

## 🌍 Supported Crops & Regions

**Crops:** Rice, Wheat, Maize, Millet, Soybean

**Regions with data:** India, United States, Nigeria (expandable)

## 🧠 AI Research Areas Covered

- ✅ Multimodal Data Fusion
- ✅ Retrieval-Augmented Generation (RAG)
- ✅ LLM-based Reasoning Chains
- ✅ Confidence Calibration
- ✅ Explainable AI (source attribution)
- ✅ Time-Series Analysis
- ✅ Domain-Specific Knowledge Bases
- ✅ AI Agents (tool-use orchestration)

## 📝 License

MIT — Free for research and commercial use.
