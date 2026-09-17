# 🚀 Quick Reference Guide

## One-Command Deployment

```bash
# Full stack with Docker
docker-compose up -d

# Verify all services running
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Pull LLM models (one-time)
docker exec agricopilot-ollama ollama pull mistral
docker exec agricopilot-ollama ollama pull nomic-embed-text

# Stop all services
docker-compose down

# Clean everything (removes volumes too)
docker-compose down -v
```

---

## Local Development Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Run backend
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

---

## API Testing

### Analyze Endpoint
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 20.5937,
    "longitude": 78.9629,
    "crop": "rice",
    "planting_date": "2024-06-15",
    "days_ahead": 30
  }' | jq .
```

### Chat Endpoint (with RAG)
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 20.5937,
    "longitude": 78.9629,
    "crop": "rice",
    "query": "Should I irrigate now?"
  }' | jq .
```

---

## Testing & Code Quality

```bash
# Run all tests
cd backend
pytest tests/ -v

# Run specific test
pytest tests/test_pipeline.py::TestYieldForecaster -v

# Coverage report
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html

# Lint
flake8 backend --max-line-length=120

# Type check
mypy backend --ignore-missing-imports
```

---

## Data Source Status

| Source | API | Status | Notes |
|---|---|---|---|
| Weather | Open-Meteo | ✅ Free | No API key needed |
| Soil | SoilGrids | ✅ Free | ~1km grid resolution |
| Market | FAO STAT | ✅ Free | Updated daily |
| NASA Power | NASA Power | ✅ Free | Historical only |
| Disease | ML Model | ✅ Built-in | Temp/humidity based |
| Satellites | Sentinel-2 | 🔄 Future | Optional enhancement |

---

## Environment Variables

See `.env.example`:
```bash
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=mistral
EMBEDDING_MODEL=nomic-embed-text
CHROMA_PERSIST_DIR=./chroma_db
DEBUG=False
LOG_LEVEL=INFO
```

---

## Troubleshooting

### Backend won't connect to Ollama
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Pull models if missing
docker exec agricopilot-ollama ollama pull mistral
```

### ChromaDB permissions error
```bash
# Fix permissions
sudo chown -R $USER backend/chroma_db
```

### Tests failing
```bash
# Clear cache
rm -rf backend/__pycache__ backend/.pytest_cache

# Reinstall dependencies
pip install --force-reinstall -r backend/requirements.txt
```

### Port already in use
```bash
# Change in docker-compose.yml or .env
# E.g., map 8001:8000 instead of 8000:8000
docker-compose down && docker-compose up -d
```

---

## Database & Cache Reset

```bash
# Clear vector store (ChromaDB)
rm -rf backend/chroma_db

# Clear pytest cache
rm -rf backend/.pytest_cache

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
```

---

## Useful Commands

```bash
# Check container logs
docker logs agricopilot-backend

# SSH into running container
docker exec -it agricopilot-backend /bin/bash

# Test frontend build
cd frontend && npm run build

# Inspect network
docker network inspect agricopilot_agricopilot-net
```

---

## CI/CD

### GitHub Actions (Auto-triggered on push)
- Runs tests
- Lints code
- Builds Docker images
- Security scan

View results: GitHub → Actions tab

### Manual Trigger
```bash
# Simulate local CI
cd backend && pytest tests/ -v && flake8 . --max-line-length=120
cd ../frontend && npm run lint && npm run build
```

---

## Deployment Checklist

- [ ] `.env` configured (not committed)
- [ ] `docker-compose.yml` reviewed
- [ ] Models pulled (`ollama pull mistral`)
- [ ] Tests passing (`pytest tests/ -v`)
- [ ] Frontend builds (`npm run build`)
- [ ] API endpoints responding (`curl http://localhost:8000/health`)
- [ ] No sensitive data in repo (use `.env`)
- [ ] All services healthy (`docker-compose ps`)

---

## Performance Tips

```bash
# Run backend with multiple workers (production)
docker-compose exec backend uvicorn main:app --workers 4 --host 0.0.0.0

# Monitor resource usage
docker stats

# Optimize ChromaDB queries (add indexing if needed)
# Edit backend/rag/knowledge_base.py
```

---

## Documentation Map

- **ARCHITECTURE.md** → System design & rationale
- **IMPLEMENTATION_SUMMARY.md** → What was built & roadmap
- **README.md** (root) → Project overview
- **backend/requirements.txt** → Python dependencies
- **frontend/package.json** → Node dependencies
- **.env.example** → Configuration template
- **docker-compose.yml** → Container orchestration
- **.github/workflows/ci.yml** → CI/CD pipeline

---

## Emergency Commands

```bash
# Nuke everything
docker-compose down -v && rm -rf backend/chroma_db

# Fresh rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# View real-time logs (all services)
docker-compose logs -f

# Debug network
docker exec agricopilot-backend ping ollama
docker exec agricopilot-backend curl http://chroma:8000/health
```

---

**Questions?** Check ARCHITECTURE.md or open an issue. 🌾
