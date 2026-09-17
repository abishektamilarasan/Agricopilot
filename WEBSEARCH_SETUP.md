# Web Search API Setup Guide

## Why Tavily Instead of DuckDuckGo?

| Feature | Tavily | DuckDuckGo |
|---|---|---|
| Official Public API | ✅ Yes | ❌ No |
| Free Tier | 500 queries/month | N/A |
| LLM-Optimized Summaries | ✅ Yes | ❌ No |
| Legal Status | ✅ Safe | ⚠️ ToS violation |
| Reliability | ✅ 99.9% uptime | ⚠️ Scraping unstable |
| Response Format | JSON (structured) | HTML (requires parsing) |

**We used Tavily** because it's the only official, legal, LLM-friendly web search API with a generous free tier.

---

## 🚀 Quick Setup (2 minutes)

### Step 1: Sign Up for Tavily
```bash
# Go to https://tavily.com
# Click "Sign Up"
# Create account (free)
# Dashboard → API Keys
# Copy your API key (starts with tvly-)
```

### Step 2: Add to .env
```bash
# Edit .env in project root
TAVILY_API_KEY=tvly-YOUR_KEY_HERE
```

### Step 3: Test
```bash
docker-compose up -d
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 20.5937,
    "longitude": 78.9629,
    "crop": "rice",
    "message": "What should I do for leaf blast disease?"
  }'
```

**Response will include:**
- LLM reasoning
- Web search results embedded
- Source attribution

---

## 📊 Free Tier Limits

- **500 queries/month** (16/day average)
- Perfect for pilot phase with 50-100 farmers
- For production: upgrade to paid ($10-50/month depending on volume)

### Usage Tips
- Cache common queries in your knowledge base
- Each farmer question = 1 API call
- Bulk queries (batch operations) available

---

## 🔧 How It Works Behind the Scenes

### Flow: Farmer Asks Question

```
1. Farmer: "Should I apply fungicide now?"

2. Backend:
   - Detects keywords: "fungicide", "disease"
   - Calls: searcher.search_disease("apply fungicide", "rice")

3. Tavily API:
   - Searches web for "apply fungicide rice India management"
   - Returns 5 most relevant results + AI summary

4. LLM receives context:
   - Local weather (current moisture, temp)
   - Local soil data (pH, fertility)
   - Disease history (from RAG)
   - **Web search results** (latest advice)
   - System prompt (AgriCopilot instructions)

5. LLM responds:
   - "Yes, fungicide recommended because: [reasoning]"
   - Cites: soil, weather, web sources
```

### Response Structure
```json
{
  "response": "Yes, apply fungicide now. Water stress is high (0.72), temperature is 26°C, and leaf blast risk is 0.55. Recent research shows...",
  "sources_used": [
    "weather (open-meteo)",
    "soil (soilgrids)",
    "knowledge-base (RAG)",
    "live web search (Tavily)"
  ],
  "confidence": 0.78
}
```

---

## 🎯 Query Types & Search Strategies

### Disease Questions
```python
Farmer: "My rice has yellow spots"

System detects: ["yellow", "spots", "disease"]
Calls: search_disease("yellow spots rice", "rice")

Tavily searches: "rice yellow spots disease identification treatment"
```

### Weather Impact
```python
Farmer: "When should I plant with this rain coming?"

System detects: ["rain", "when", "plant"]
Calls: search_weather_impact("rice", "India")

Tavily searches: "rice planting weather impact rain India"
```

### Market Questions
```python
Farmer: "What's rice price now?"

System detects: ["price", "market", "sell"]
Calls: search_market_price("rice", "India")

Tavily searches: "rice price India market today"
```

### Fertilizer
```python
Farmer: "How much fertilizer for rice?"

System detects: ["fertilizer", "how much"]
Calls: search_fertilizer_guide("rice")

Tavily searches: "rice fertilizer dosage npk application timing"
```

---

## 📈 Scaling Beyond Free Tier

### Month 1: Pilot (50 farmers)
- ~1000 queries = 2× free limit
- **Cost:** Upgrade to basic plan ($10/month)

### Month 6: Growth (500 farmers)
- ~15,000 queries = 30× free limit
- **Cost:** Mid-tier plan ($50/month)

### Year 1: Production (5000 farmers)
- ~150,000 queries = 300× free limit
- **Cost:** Enterprise plan ($200-500/month)

**Or:** Cache answers locally (TNAU knowledge base → reduces web searches)

---

## ✅ Verification Checklist

After setup, verify with this test script:

```bash
# backend/test_web_search.py
import asyncio
from data_sources.web_search import searcher

async def test():
    # Test 1: Disease search
    result = await searcher.search_disease("leaf blast", "rice")
    print("Disease search:", result["status"])
    
    # Test 2: Weather search
    result = await searcher.search_weather_impact("rice", "India")
    print("Weather search:", result["status"])
    
    # Test 3: Market search
    result = await searcher.search_market_price("rice", "India")
    print("Market search:", result["status"])
    
    # Test 4: Fertilizer search
    result = await searcher.search_fertilizer_guide("rice")
    print("Fertilizer search:", result["status"])

asyncio.run(test())
```

Run:
```bash
cd backend
python test_web_search.py
```

Expected output:
```
Disease search: success
Weather search: success
Market search: success
Fertilizer search: success
```

---

## 🐛 Troubleshooting

### "Web search API not configured"
- **Cause:** TAVILY_API_KEY not set in .env
- **Fix:** Add key, restart container: `docker-compose restart backend`

### "Tavily API error: 401"
- **Cause:** Invalid API key
- **Fix:** Get correct key from https://tavily.com/dashboard

### "Tavily API error: 429"
- **Cause:** Rate limit exceeded (>500/month)
- **Fix:** Upgrade plan or implement caching

### "Timeout after 10 seconds"
- **Cause:** Internet connection or Tavily down
- **Fix:** Falls back gracefully; check `docker logs backend`

---

## 🔐 Security Notes

1. **API Key:** Keep in `.env`, never commit
2. **Rate limits:** Tavily prevents abuse automatically
3. **Data privacy:** Queries logged by Tavily (read their privacy policy)
4. **CORS:** Frontend → Backend only (backend does web search)

---

## 📚 Tavily Documentation

- **Docs:** https://docs.tavily.com
- **Python SDK:** Not needed (we use httpx directly)
- **API Reference:** https://docs.tavily.com/docs/tavily-api/api-reference

---

## 💡 Pro Tips

### 1. Reduce API Calls
Cache answers in your RAG knowledge base:
```python
# If web search result is high quality, save it
if search_result["confidence"] > 0.9:
    # Add to ChromaDB knowledge base
    # Next farmer with same question uses cached result
```

### 2. Smart Routing
Current system already does this, but you could add:
```python
# If user location in known region, use cached regional data
if location in CACHED_REGIONS:
    return cached_result  # Skip web search
```

### 3. Batch Processing
For bulk farmer imports:
```python
# Process 50 farmers, aggregate unique questions
# Only search web for unique queries
```

### 4. Fallback Strategy
If Tavily rate limit hit:
```python
# Gracefully fall back to RAG only
if tavily_error:
    return rag_only_response
# Chat still works, just without live web data
```

---

## 🎯 Next Steps

1. ✅ Sign up at https://tavily.com
2. ✅ Add API key to .env
3. ✅ Run `docker-compose up -d`
4. ✅ Test with farmer questions
5. ✅ Monitor usage (https://tavily.com/dashboard)

---

**Your AgriCopilot can now answer questions with real-time web data!** 🌾📱
