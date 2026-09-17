# Code Citations

## License: unknown
https://github.com/aditya-283/pufferfish-clone/blob/b4e94a22fd8a4f859528afb655732a0b082358df/models/transfer.py

```
Now I'll address all three of your questions:

---

## 🎨 **Frontend Display of 4 Forecasters**

The frontend **currently doesn't display** the 4 forecasters I built. It's showing older data (weather, soil, market, NDVI).

### **Current Frontend Shows:**
```
Temperature  |  Soil Fertility  |  Market Price  |  Confidence
```

### **What Should Be Added:**

Create a new `analytics` or `forecasts` tab showing:

```
┌─────────────────────────────────────────────────────────┐
│ FORECASTS & FACTORS                                     │
├─────────────────────────────────────────────────────────┤
│ 1. YIELD FORECAST                                       │
│    Expected: 3200 kg/ha (±200)  [73% confidence]       │
│    ├─ Soil suitability factor: 0.85                     │
│    ├─ Growing degree days: 1450°C                       │
│    ├─ Drought stress factor: 0.92                       │
│    └─ pH factor: 0.88                                   │
│                                                         │
│ 2. WATER STRESS                                         │
│    Current stress: 0.62 (moderate)  [81% confidence]   │
│    ├─ Rainfall forecast: 45mm next 7 days              │
│    ├─ ET requirement: 4.2mm/day                         │
│    ├─ Soil moisture: 62% of capacity                    │
│    └─ Recommendation: Irrigate 25mm if stress > 0.6    │
│                                                         │
│ 3. DISEASE RISK                                         │
│    Overall risk: 0.45 (low)  [68% confidence]          │
│    ├─ Blast risk: 0.55 (moderate, T: 24°C, RH: 78%)   │
│    ├─ Brown spot: 0.38 (low)                           │
│    ├─ Sheath blight: 0.42 (low)                        │
│    └─ Preventive spray: Tricyclazole if risk > 0.7    │
│                                                         │
│ 4. FERTILIZER NEED                                      │
│    Target yield: 3200 kg/ha                             │
│    ├─ N needed: 85 kg/ha (soil has 12, uptake rate 60) │
│    ├─ P needed: 40 kg/ha (soil has 8, uptake rate 15)  │
│    ├─ K needed: 40 kg/ha (soil has 120, uptake rate 20)│
│    └─ Split: Apply 30% basal, 35% tillering, 35% bloom│
└─────────────────────────────────────────────────────────┘
```

### **Code to Add to Frontend (new component)**

Create `frontend/app/components/ForecastersPanel.js`:

```javascript
export function ForecastersPanel({ forecasts }) {
  if (!forecasts) return null;

  return (
    <div className="dashboard-grid">
      {/* Yield Forecaster */}
      <div className="card">
        <h3>🌾 Yield Forecast</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.yield.estimate} kg/ha</span>
          <span className="metric-range">±{forecasts.yield.ci_range}</span>
          <ConfidenceGauge value={forecasts.yield.confidence * 100} />
        </div>
        <div className="factors">
          <div className="factor">
            <span>Soil Suitability:</span> {forecasts.yield.soil_factor}
          </div>
          <div className="factor">
            <span>Drought Stress:</span> {forecasts.yield.drought_factor}
          </div>
          <div className="factor">
            <span>pH Factor:</span> {forecasts.yield.ph_factor}
          </div>
        </div>
      </div>

      {/* Water Stress Forecaster */}
      <div className="card">
        <h3>💧 Water Stress</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.water_stress.stress_index.toFixed(2)}</span>
          <span className="metric-status">
            {forecasts.water_stress.stress_index < 0.3 ? '🔴 Dry' : 
             forecasts.water_stress.stress_index < 0.6 ? '🟡 Moderate' : '🟢 Wet'}
          </span>
        </div>
        <div className="factors">
          <div>Rainfall: {forecasts.water_stress.rainfall}mm</div>
          <div>ET: {forecasts.water_stress.et}mm</div>
          <div>Soil Moisture: {forecasts.water_stress.soil_moisture}%</div>
        </div>
      </div>

      {/* Disease Risk Forecaster */}
      <div className="card">
        <h3>🦠 Disease Risk</h3>
        <div className="disease-list">
          {forecasts.disease_risks.map(disease => (
            <div key={disease.name} className="disease-item">
              <span>{disease.name}</span>
              <span className={`risk-${disease.severity}`}>
                {(disease.risk * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Fertilizer Recommender */}
      <div className="card">
        <h3>🌱 Fertilizer Need</h3>
        <div className="nutrient-grid">
          <div className="nutrient">
            <span className="nutrient-label">N</span>
            <span className="nutrient-value">{forecasts.fertilizer.n} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">P</span>
            <span className="nutrient-value">{forecasts.fertilizer.p} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">K</span>
            <span className="nutrient-value">{forecasts.fertilizer.k} kg/ha</span>
          </div>
        </div>
        <div className="split-schedule">
          <div>📅 Basal: 30%</div>
          <div>🌱 Tillering: 35%</div>
          <div>🌸 Bloom: 35%</div>
        </div>
      </div>
    </div>
  );
}
```

---

## 🔍 **DuckDuckGo API for Web Search**

DuckDuckGo does **NOT have an official public API**, but there are workarounds:

### **Option 1: Use Existing Alternative (Recommended)**
```python
# Use Free APIs instead of DuckDuckGo
# Option A: Google Custom Search (limited free tier)
# Option B: Bing Search API (Azure required, ~$7/month)
# Option C: Metaphor API (AI-focused search, free tier)
```

### **Option 2: Web Scraping DuckDuckGo (Not Recommended)**
```python
# Violates ToS, prone to breakage
import requests
from bs4 import BeautifulSoup

def search_duckduckgo(query):
    url = f"https://html.duckduckgo.com/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0..."}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Extract results...
```

### **Option 3: Use Tavily Search API (Free Tier)**
```python
# Better alternative specifically for LLM context
pip install tavily-python

from tavily import TavilyClient

client = TavilyClient(api_key="your_key")
results = client.search(
    query="rice disease identification",
    include_answer=True
)
# Returns: [{"title": "...", "url": "...", "content": "..."}, ...]
```

**What I Recommend:** Add a **web search button** to copilot that uses **Tavily** (free tier) to fetch recent agriculture news/research for context.

---

## 📸 **ML Routes for Image Diagnosis**

### **YES, it's still there!** ✅

**Location:** `backend/api/ml_routes.py`

**Current Status:**
- ✅ Endpoint exists: `POST /api/diagnose`
- ✅ Accepts image upload
- ✅ Saves file to `backend/uploads/`
- ⚠️ Returns **placeholder** responses (random diseases)
- ❌ No actual ML model integrated yet

**To Add Real ML Model:**

### **Step 1: Create ML Model Script**

Create `backend/ml_models/disease_classifier.py`:

```python
import torch
from torchvision import transforms, models
from PIL import Image
import json

# Load pre-trained model (e.g., ResNet50 trained on plant diseases)
model = models.resnet50(pretrained=True)
# Finetune on your disease dataset

class PlantDiseaseClassifier:
    def __init__(self, model_path):
        self.model = torch.load(model_path)
        self.model.eval()
        self.diseases = {
            0: "Healthy Leaf",
            1: "Leaf Blast",
            2: "Brown Spot",
            3: "Sheath Blight",
            4: "Nitrogen Deficiency",
            5: "Phosphorus Deficiency"
        }
        
    def predict(self, image_path):
        image = Image.open(image_path).convert('RGB')
        image_tensor = transforms.Compose([
            transforms.Resize((
```


## License: unknown
https://github.com/aditya-283/pufferfish-clone/blob/b4e94a22fd8a4f859528afb655732a0b082358df/models/transfer.py

```
Now I'll address all three of your questions:

---

## 🎨 **Frontend Display of 4 Forecasters**

The frontend **currently doesn't display** the 4 forecasters I built. It's showing older data (weather, soil, market, NDVI).

### **Current Frontend Shows:**
```
Temperature  |  Soil Fertility  |  Market Price  |  Confidence
```

### **What Should Be Added:**

Create a new `analytics` or `forecasts` tab showing:

```
┌─────────────────────────────────────────────────────────┐
│ FORECASTS & FACTORS                                     │
├─────────────────────────────────────────────────────────┤
│ 1. YIELD FORECAST                                       │
│    Expected: 3200 kg/ha (±200)  [73% confidence]       │
│    ├─ Soil suitability factor: 0.85                     │
│    ├─ Growing degree days: 1450°C                       │
│    ├─ Drought stress factor: 0.92                       │
│    └─ pH factor: 0.88                                   │
│                                                         │
│ 2. WATER STRESS                                         │
│    Current stress: 0.62 (moderate)  [81% confidence]   │
│    ├─ Rainfall forecast: 45mm next 7 days              │
│    ├─ ET requirement: 4.2mm/day                         │
│    ├─ Soil moisture: 62% of capacity                    │
│    └─ Recommendation: Irrigate 25mm if stress > 0.6    │
│                                                         │
│ 3. DISEASE RISK                                         │
│    Overall risk: 0.45 (low)  [68% confidence]          │
│    ├─ Blast risk: 0.55 (moderate, T: 24°C, RH: 78%)   │
│    ├─ Brown spot: 0.38 (low)                           │
│    ├─ Sheath blight: 0.42 (low)                        │
│    └─ Preventive spray: Tricyclazole if risk > 0.7    │
│                                                         │
│ 4. FERTILIZER NEED                                      │
│    Target yield: 3200 kg/ha                             │
│    ├─ N needed: 85 kg/ha (soil has 12, uptake rate 60) │
│    ├─ P needed: 40 kg/ha (soil has 8, uptake rate 15)  │
│    ├─ K needed: 40 kg/ha (soil has 120, uptake rate 20)│
│    └─ Split: Apply 30% basal, 35% tillering, 35% bloom│
└─────────────────────────────────────────────────────────┘
```

### **Code to Add to Frontend (new component)**

Create `frontend/app/components/ForecastersPanel.js`:

```javascript
export function ForecastersPanel({ forecasts }) {
  if (!forecasts) return null;

  return (
    <div className="dashboard-grid">
      {/* Yield Forecaster */}
      <div className="card">
        <h3>🌾 Yield Forecast</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.yield.estimate} kg/ha</span>
          <span className="metric-range">±{forecasts.yield.ci_range}</span>
          <ConfidenceGauge value={forecasts.yield.confidence * 100} />
        </div>
        <div className="factors">
          <div className="factor">
            <span>Soil Suitability:</span> {forecasts.yield.soil_factor}
          </div>
          <div className="factor">
            <span>Drought Stress:</span> {forecasts.yield.drought_factor}
          </div>
          <div className="factor">
            <span>pH Factor:</span> {forecasts.yield.ph_factor}
          </div>
        </div>
      </div>

      {/* Water Stress Forecaster */}
      <div className="card">
        <h3>💧 Water Stress</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.water_stress.stress_index.toFixed(2)}</span>
          <span className="metric-status">
            {forecasts.water_stress.stress_index < 0.3 ? '🔴 Dry' : 
             forecasts.water_stress.stress_index < 0.6 ? '🟡 Moderate' : '🟢 Wet'}
          </span>
        </div>
        <div className="factors">
          <div>Rainfall: {forecasts.water_stress.rainfall}mm</div>
          <div>ET: {forecasts.water_stress.et}mm</div>
          <div>Soil Moisture: {forecasts.water_stress.soil_moisture}%</div>
        </div>
      </div>

      {/* Disease Risk Forecaster */}
      <div className="card">
        <h3>🦠 Disease Risk</h3>
        <div className="disease-list">
          {forecasts.disease_risks.map(disease => (
            <div key={disease.name} className="disease-item">
              <span>{disease.name}</span>
              <span className={`risk-${disease.severity}`}>
                {(disease.risk * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Fertilizer Recommender */}
      <div className="card">
        <h3>🌱 Fertilizer Need</h3>
        <div className="nutrient-grid">
          <div className="nutrient">
            <span className="nutrient-label">N</span>
            <span className="nutrient-value">{forecasts.fertilizer.n} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">P</span>
            <span className="nutrient-value">{forecasts.fertilizer.p} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">K</span>
            <span className="nutrient-value">{forecasts.fertilizer.k} kg/ha</span>
          </div>
        </div>
        <div className="split-schedule">
          <div>📅 Basal: 30%</div>
          <div>🌱 Tillering: 35%</div>
          <div>🌸 Bloom: 35%</div>
        </div>
      </div>
    </div>
  );
}
```

---

## 🔍 **DuckDuckGo API for Web Search**

DuckDuckGo does **NOT have an official public API**, but there are workarounds:

### **Option 1: Use Existing Alternative (Recommended)**
```python
# Use Free APIs instead of DuckDuckGo
# Option A: Google Custom Search (limited free tier)
# Option B: Bing Search API (Azure required, ~$7/month)
# Option C: Metaphor API (AI-focused search, free tier)
```

### **Option 2: Web Scraping DuckDuckGo (Not Recommended)**
```python
# Violates ToS, prone to breakage
import requests
from bs4 import BeautifulSoup

def search_duckduckgo(query):
    url = f"https://html.duckduckgo.com/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0..."}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Extract results...
```

### **Option 3: Use Tavily Search API (Free Tier)**
```python
# Better alternative specifically for LLM context
pip install tavily-python

from tavily import TavilyClient

client = TavilyClient(api_key="your_key")
results = client.search(
    query="rice disease identification",
    include_answer=True
)
# Returns: [{"title": "...", "url": "...", "content": "..."}, ...]
```

**What I Recommend:** Add a **web search button** to copilot that uses **Tavily** (free tier) to fetch recent agriculture news/research for context.

---

## 📸 **ML Routes for Image Diagnosis**

### **YES, it's still there!** ✅

**Location:** `backend/api/ml_routes.py`

**Current Status:**
- ✅ Endpoint exists: `POST /api/diagnose`
- ✅ Accepts image upload
- ✅ Saves file to `backend/uploads/`
- ⚠️ Returns **placeholder** responses (random diseases)
- ❌ No actual ML model integrated yet

**To Add Real ML Model:**

### **Step 1: Create ML Model Script**

Create `backend/ml_models/disease_classifier.py`:

```python
import torch
from torchvision import transforms, models
from PIL import Image
import json

# Load pre-trained model (e.g., ResNet50 trained on plant diseases)
model = models.resnet50(pretrained=True)
# Finetune on your disease dataset

class PlantDiseaseClassifier:
    def __init__(self, model_path):
        self.model = torch.load(model_path)
        self.model.eval()
        self.diseases = {
            0: "Healthy Leaf",
            1: "Leaf Blast",
            2: "Brown Spot",
            3: "Sheath Blight",
            4: "Nitrogen Deficiency",
            5: "Phosphorus Deficiency"
        }
        
    def predict(self, image_path):
        image = Image.open(image_path).convert('RGB')
        image_tensor = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.
```


## License: unknown
https://github.com/aditya-283/pufferfish-clone/blob/b4e94a22fd8a4f859528afb655732a0b082358df/models/transfer.py

```
Now I'll address all three of your questions:

---

## 🎨 **Frontend Display of 4 Forecasters**

The frontend **currently doesn't display** the 4 forecasters I built. It's showing older data (weather, soil, market, NDVI).

### **Current Frontend Shows:**
```
Temperature  |  Soil Fertility  |  Market Price  |  Confidence
```

### **What Should Be Added:**

Create a new `analytics` or `forecasts` tab showing:

```
┌─────────────────────────────────────────────────────────┐
│ FORECASTS & FACTORS                                     │
├─────────────────────────────────────────────────────────┤
│ 1. YIELD FORECAST                                       │
│    Expected: 3200 kg/ha (±200)  [73% confidence]       │
│    ├─ Soil suitability factor: 0.85                     │
│    ├─ Growing degree days: 1450°C                       │
│    ├─ Drought stress factor: 0.92                       │
│    └─ pH factor: 0.88                                   │
│                                                         │
│ 2. WATER STRESS                                         │
│    Current stress: 0.62 (moderate)  [81% confidence]   │
│    ├─ Rainfall forecast: 45mm next 7 days              │
│    ├─ ET requirement: 4.2mm/day                         │
│    ├─ Soil moisture: 62% of capacity                    │
│    └─ Recommendation: Irrigate 25mm if stress > 0.6    │
│                                                         │
│ 3. DISEASE RISK                                         │
│    Overall risk: 0.45 (low)  [68% confidence]          │
│    ├─ Blast risk: 0.55 (moderate, T: 24°C, RH: 78%)   │
│    ├─ Brown spot: 0.38 (low)                           │
│    ├─ Sheath blight: 0.42 (low)                        │
│    └─ Preventive spray: Tricyclazole if risk > 0.7    │
│                                                         │
│ 4. FERTILIZER NEED                                      │
│    Target yield: 3200 kg/ha                             │
│    ├─ N needed: 85 kg/ha (soil has 12, uptake rate 60) │
│    ├─ P needed: 40 kg/ha (soil has 8, uptake rate 15)  │
│    ├─ K needed: 40 kg/ha (soil has 120, uptake rate 20)│
│    └─ Split: Apply 30% basal, 35% tillering, 35% bloom│
└─────────────────────────────────────────────────────────┘
```

### **Code to Add to Frontend (new component)**

Create `frontend/app/components/ForecastersPanel.js`:

```javascript
export function ForecastersPanel({ forecasts }) {
  if (!forecasts) return null;

  return (
    <div className="dashboard-grid">
      {/* Yield Forecaster */}
      <div className="card">
        <h3>🌾 Yield Forecast</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.yield.estimate} kg/ha</span>
          <span className="metric-range">±{forecasts.yield.ci_range}</span>
          <ConfidenceGauge value={forecasts.yield.confidence * 100} />
        </div>
        <div className="factors">
          <div className="factor">
            <span>Soil Suitability:</span> {forecasts.yield.soil_factor}
          </div>
          <div className="factor">
            <span>Drought Stress:</span> {forecasts.yield.drought_factor}
          </div>
          <div className="factor">
            <span>pH Factor:</span> {forecasts.yield.ph_factor}
          </div>
        </div>
      </div>

      {/* Water Stress Forecaster */}
      <div className="card">
        <h3>💧 Water Stress</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.water_stress.stress_index.toFixed(2)}</span>
          <span className="metric-status">
            {forecasts.water_stress.stress_index < 0.3 ? '🔴 Dry' : 
             forecasts.water_stress.stress_index < 0.6 ? '🟡 Moderate' : '🟢 Wet'}
          </span>
        </div>
        <div className="factors">
          <div>Rainfall: {forecasts.water_stress.rainfall}mm</div>
          <div>ET: {forecasts.water_stress.et}mm</div>
          <div>Soil Moisture: {forecasts.water_stress.soil_moisture}%</div>
        </div>
      </div>

      {/* Disease Risk Forecaster */}
      <div className="card">
        <h3>🦠 Disease Risk</h3>
        <div className="disease-list">
          {forecasts.disease_risks.map(disease => (
            <div key={disease.name} className="disease-item">
              <span>{disease.name}</span>
              <span className={`risk-${disease.severity}`}>
                {(disease.risk * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Fertilizer Recommender */}
      <div className="card">
        <h3>🌱 Fertilizer Need</h3>
        <div className="nutrient-grid">
          <div className="nutrient">
            <span className="nutrient-label">N</span>
            <span className="nutrient-value">{forecasts.fertilizer.n} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">P</span>
            <span className="nutrient-value">{forecasts.fertilizer.p} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">K</span>
            <span className="nutrient-value">{forecasts.fertilizer.k} kg/ha</span>
          </div>
        </div>
        <div className="split-schedule">
          <div>📅 Basal: 30%</div>
          <div>🌱 Tillering: 35%</div>
          <div>🌸 Bloom: 35%</div>
        </div>
      </div>
    </div>
  );
}
```

---

## 🔍 **DuckDuckGo API for Web Search**

DuckDuckGo does **NOT have an official public API**, but there are workarounds:

### **Option 1: Use Existing Alternative (Recommended)**
```python
# Use Free APIs instead of DuckDuckGo
# Option A: Google Custom Search (limited free tier)
# Option B: Bing Search API (Azure required, ~$7/month)
# Option C: Metaphor API (AI-focused search, free tier)
```

### **Option 2: Web Scraping DuckDuckGo (Not Recommended)**
```python
# Violates ToS, prone to breakage
import requests
from bs4 import BeautifulSoup

def search_duckduckgo(query):
    url = f"https://html.duckduckgo.com/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0..."}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Extract results...
```

### **Option 3: Use Tavily Search API (Free Tier)**
```python
# Better alternative specifically for LLM context
pip install tavily-python

from tavily import TavilyClient

client = TavilyClient(api_key="your_key")
results = client.search(
    query="rice disease identification",
    include_answer=True
)
# Returns: [{"title": "...", "url": "...", "content": "..."}, ...]
```

**What I Recommend:** Add a **web search button** to copilot that uses **Tavily** (free tier) to fetch recent agriculture news/research for context.

---

## 📸 **ML Routes for Image Diagnosis**

### **YES, it's still there!** ✅

**Location:** `backend/api/ml_routes.py`

**Current Status:**
- ✅ Endpoint exists: `POST /api/diagnose`
- ✅ Accepts image upload
- ✅ Saves file to `backend/uploads/`
- ⚠️ Returns **placeholder** responses (random diseases)
- ❌ No actual ML model integrated yet

**To Add Real ML Model:**

### **Step 1: Create ML Model Script**

Create `backend/ml_models/disease_classifier.py`:

```python
import torch
from torchvision import transforms, models
from PIL import Image
import json

# Load pre-trained model (e.g., ResNet50 trained on plant diseases)
model = models.resnet50(pretrained=True)
# Finetune on your disease dataset

class PlantDiseaseClassifier:
    def __init__(self, model_path):
        self.model = torch.load(model_path)
        self.model.eval()
        self.diseases = {
            0: "Healthy Leaf",
            1: "Leaf Blast",
            2: "Brown Spot",
            3: "Sheath Blight",
            4: "Nitrogen Deficiency",
            5: "Phosphorus Deficiency"
        }
        
    def predict(self, image_path):
        image = Image.open(image_path).convert('RGB')
        image_tensor = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.
```


## License: unknown
https://github.com/aditya-283/pufferfish-clone/blob/b4e94a22fd8a4f859528afb655732a0b082358df/models/transfer.py

```
Now I'll address all three of your questions:

---

## 🎨 **Frontend Display of 4 Forecasters**

The frontend **currently doesn't display** the 4 forecasters I built. It's showing older data (weather, soil, market, NDVI).

### **Current Frontend Shows:**
```
Temperature  |  Soil Fertility  |  Market Price  |  Confidence
```

### **What Should Be Added:**

Create a new `analytics` or `forecasts` tab showing:

```
┌─────────────────────────────────────────────────────────┐
│ FORECASTS & FACTORS                                     │
├─────────────────────────────────────────────────────────┤
│ 1. YIELD FORECAST                                       │
│    Expected: 3200 kg/ha (±200)  [73% confidence]       │
│    ├─ Soil suitability factor: 0.85                     │
│    ├─ Growing degree days: 1450°C                       │
│    ├─ Drought stress factor: 0.92                       │
│    └─ pH factor: 0.88                                   │
│                                                         │
│ 2. WATER STRESS                                         │
│    Current stress: 0.62 (moderate)  [81% confidence]   │
│    ├─ Rainfall forecast: 45mm next 7 days              │
│    ├─ ET requirement: 4.2mm/day                         │
│    ├─ Soil moisture: 62% of capacity                    │
│    └─ Recommendation: Irrigate 25mm if stress > 0.6    │
│                                                         │
│ 3. DISEASE RISK                                         │
│    Overall risk: 0.45 (low)  [68% confidence]          │
│    ├─ Blast risk: 0.55 (moderate, T: 24°C, RH: 78%)   │
│    ├─ Brown spot: 0.38 (low)                           │
│    ├─ Sheath blight: 0.42 (low)                        │
│    └─ Preventive spray: Tricyclazole if risk > 0.7    │
│                                                         │
│ 4. FERTILIZER NEED                                      │
│    Target yield: 3200 kg/ha                             │
│    ├─ N needed: 85 kg/ha (soil has 12, uptake rate 60) │
│    ├─ P needed: 40 kg/ha (soil has 8, uptake rate 15)  │
│    ├─ K needed: 40 kg/ha (soil has 120, uptake rate 20)│
│    └─ Split: Apply 30% basal, 35% tillering, 35% bloom│
└─────────────────────────────────────────────────────────┘
```

### **Code to Add to Frontend (new component)**

Create `frontend/app/components/ForecastersPanel.js`:

```javascript
export function ForecastersPanel({ forecasts }) {
  if (!forecasts) return null;

  return (
    <div className="dashboard-grid">
      {/* Yield Forecaster */}
      <div className="card">
        <h3>🌾 Yield Forecast</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.yield.estimate} kg/ha</span>
          <span className="metric-range">±{forecasts.yield.ci_range}</span>
          <ConfidenceGauge value={forecasts.yield.confidence * 100} />
        </div>
        <div className="factors">
          <div className="factor">
            <span>Soil Suitability:</span> {forecasts.yield.soil_factor}
          </div>
          <div className="factor">
            <span>Drought Stress:</span> {forecasts.yield.drought_factor}
          </div>
          <div className="factor">
            <span>pH Factor:</span> {forecasts.yield.ph_factor}
          </div>
        </div>
      </div>

      {/* Water Stress Forecaster */}
      <div className="card">
        <h3>💧 Water Stress</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.water_stress.stress_index.toFixed(2)}</span>
          <span className="metric-status">
            {forecasts.water_stress.stress_index < 0.3 ? '🔴 Dry' : 
             forecasts.water_stress.stress_index < 0.6 ? '🟡 Moderate' : '🟢 Wet'}
          </span>
        </div>
        <div className="factors">
          <div>Rainfall: {forecasts.water_stress.rainfall}mm</div>
          <div>ET: {forecasts.water_stress.et}mm</div>
          <div>Soil Moisture: {forecasts.water_stress.soil_moisture}%</div>
        </div>
      </div>

      {/* Disease Risk Forecaster */}
      <div className="card">
        <h3>🦠 Disease Risk</h3>
        <div className="disease-list">
          {forecasts.disease_risks.map(disease => (
            <div key={disease.name} className="disease-item">
              <span>{disease.name}</span>
              <span className={`risk-${disease.severity}`}>
                {(disease.risk * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Fertilizer Recommender */}
      <div className="card">
        <h3>🌱 Fertilizer Need</h3>
        <div className="nutrient-grid">
          <div className="nutrient">
            <span className="nutrient-label">N</span>
            <span className="nutrient-value">{forecasts.fertilizer.n} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">P</span>
            <span className="nutrient-value">{forecasts.fertilizer.p} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">K</span>
            <span className="nutrient-value">{forecasts.fertilizer.k} kg/ha</span>
          </div>
        </div>
        <div className="split-schedule">
          <div>📅 Basal: 30%</div>
          <div>🌱 Tillering: 35%</div>
          <div>🌸 Bloom: 35%</div>
        </div>
      </div>
    </div>
  );
}
```

---

## 🔍 **DuckDuckGo API for Web Search**

DuckDuckGo does **NOT have an official public API**, but there are workarounds:

### **Option 1: Use Existing Alternative (Recommended)**
```python
# Use Free APIs instead of DuckDuckGo
# Option A: Google Custom Search (limited free tier)
# Option B: Bing Search API (Azure required, ~$7/month)
# Option C: Metaphor API (AI-focused search, free tier)
```

### **Option 2: Web Scraping DuckDuckGo (Not Recommended)**
```python
# Violates ToS, prone to breakage
import requests
from bs4 import BeautifulSoup

def search_duckduckgo(query):
    url = f"https://html.duckduckgo.com/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0..."}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Extract results...
```

### **Option 3: Use Tavily Search API (Free Tier)**
```python
# Better alternative specifically for LLM context
pip install tavily-python

from tavily import TavilyClient

client = TavilyClient(api_key="your_key")
results = client.search(
    query="rice disease identification",
    include_answer=True
)
# Returns: [{"title": "...", "url": "...", "content": "..."}, ...]
```

**What I Recommend:** Add a **web search button** to copilot that uses **Tavily** (free tier) to fetch recent agriculture news/research for context.

---

## 📸 **ML Routes for Image Diagnosis**

### **YES, it's still there!** ✅

**Location:** `backend/api/ml_routes.py`

**Current Status:**
- ✅ Endpoint exists: `POST /api/diagnose`
- ✅ Accepts image upload
- ✅ Saves file to `backend/uploads/`
- ⚠️ Returns **placeholder** responses (random diseases)
- ❌ No actual ML model integrated yet

**To Add Real ML Model:**

### **Step 1: Create ML Model Script**

Create `backend/ml_models/disease_classifier.py`:

```python
import torch
from torchvision import transforms, models
from PIL import Image
import json

# Load pre-trained model (e.g., ResNet50 trained on plant diseases)
model = models.resnet50(pretrained=True)
# Finetune on your disease dataset

class PlantDiseaseClassifier:
    def __init__(self, model_path):
        self.model = torch.load(model_path)
        self.model.eval()
        self.diseases = {
            0: "Healthy Leaf",
            1: "Leaf Blast",
            2: "Brown Spot",
            3: "Sheath Blight",
            4: "Nitrogen Deficiency",
            5: "Phosphorus Deficiency"
        }
        
    def predict(self, image_path):
        image = Image.open(image_path).convert('RGB')
        image_tensor = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0
```


## License: unknown
https://github.com/aditya-283/pufferfish-clone/blob/b4e94a22fd8a4f859528afb655732a0b082358df/models/transfer.py

```
Now I'll address all three of your questions:

---

## 🎨 **Frontend Display of 4 Forecasters**

The frontend **currently doesn't display** the 4 forecasters I built. It's showing older data (weather, soil, market, NDVI).

### **Current Frontend Shows:**
```
Temperature  |  Soil Fertility  |  Market Price  |  Confidence
```

### **What Should Be Added:**

Create a new `analytics` or `forecasts` tab showing:

```
┌─────────────────────────────────────────────────────────┐
│ FORECASTS & FACTORS                                     │
├─────────────────────────────────────────────────────────┤
│ 1. YIELD FORECAST                                       │
│    Expected: 3200 kg/ha (±200)  [73% confidence]       │
│    ├─ Soil suitability factor: 0.85                     │
│    ├─ Growing degree days: 1450°C                       │
│    ├─ Drought stress factor: 0.92                       │
│    └─ pH factor: 0.88                                   │
│                                                         │
│ 2. WATER STRESS                                         │
│    Current stress: 0.62 (moderate)  [81% confidence]   │
│    ├─ Rainfall forecast: 45mm next 7 days              │
│    ├─ ET requirement: 4.2mm/day                         │
│    ├─ Soil moisture: 62% of capacity                    │
│    └─ Recommendation: Irrigate 25mm if stress > 0.6    │
│                                                         │
│ 3. DISEASE RISK                                         │
│    Overall risk: 0.45 (low)  [68% confidence]          │
│    ├─ Blast risk: 0.55 (moderate, T: 24°C, RH: 78%)   │
│    ├─ Brown spot: 0.38 (low)                           │
│    ├─ Sheath blight: 0.42 (low)                        │
│    └─ Preventive spray: Tricyclazole if risk > 0.7    │
│                                                         │
│ 4. FERTILIZER NEED                                      │
│    Target yield: 3200 kg/ha                             │
│    ├─ N needed: 85 kg/ha (soil has 12, uptake rate 60) │
│    ├─ P needed: 40 kg/ha (soil has 8, uptake rate 15)  │
│    ├─ K needed: 40 kg/ha (soil has 120, uptake rate 20)│
│    └─ Split: Apply 30% basal, 35% tillering, 35% bloom│
└─────────────────────────────────────────────────────────┘
```

### **Code to Add to Frontend (new component)**

Create `frontend/app/components/ForecastersPanel.js`:

```javascript
export function ForecastersPanel({ forecasts }) {
  if (!forecasts) return null;

  return (
    <div className="dashboard-grid">
      {/* Yield Forecaster */}
      <div className="card">
        <h3>🌾 Yield Forecast</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.yield.estimate} kg/ha</span>
          <span className="metric-range">±{forecasts.yield.ci_range}</span>
          <ConfidenceGauge value={forecasts.yield.confidence * 100} />
        </div>
        <div className="factors">
          <div className="factor">
            <span>Soil Suitability:</span> {forecasts.yield.soil_factor}
          </div>
          <div className="factor">
            <span>Drought Stress:</span> {forecasts.yield.drought_factor}
          </div>
          <div className="factor">
            <span>pH Factor:</span> {forecasts.yield.ph_factor}
          </div>
        </div>
      </div>

      {/* Water Stress Forecaster */}
      <div className="card">
        <h3>💧 Water Stress</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.water_stress.stress_index.toFixed(2)}</span>
          <span className="metric-status">
            {forecasts.water_stress.stress_index < 0.3 ? '🔴 Dry' : 
             forecasts.water_stress.stress_index < 0.6 ? '🟡 Moderate' : '🟢 Wet'}
          </span>
        </div>
        <div className="factors">
          <div>Rainfall: {forecasts.water_stress.rainfall}mm</div>
          <div>ET: {forecasts.water_stress.et}mm</div>
          <div>Soil Moisture: {forecasts.water_stress.soil_moisture}%</div>
        </div>
      </div>

      {/* Disease Risk Forecaster */}
      <div className="card">
        <h3>🦠 Disease Risk</h3>
        <div className="disease-list">
          {forecasts.disease_risks.map(disease => (
            <div key={disease.name} className="disease-item">
              <span>{disease.name}</span>
              <span className={`risk-${disease.severity}`}>
                {(disease.risk * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Fertilizer Recommender */}
      <div className="card">
        <h3>🌱 Fertilizer Need</h3>
        <div className="nutrient-grid">
          <div className="nutrient">
            <span className="nutrient-label">N</span>
            <span className="nutrient-value">{forecasts.fertilizer.n} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">P</span>
            <span className="nutrient-value">{forecasts.fertilizer.p} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">K</span>
            <span className="nutrient-value">{forecasts.fertilizer.k} kg/ha</span>
          </div>
        </div>
        <div className="split-schedule">
          <div>📅 Basal: 30%</div>
          <div>🌱 Tillering: 35%</div>
          <div>🌸 Bloom: 35%</div>
        </div>
      </div>
    </div>
  );
}
```

---

## 🔍 **DuckDuckGo API for Web Search**

DuckDuckGo does **NOT have an official public API**, but there are workarounds:

### **Option 1: Use Existing Alternative (Recommended)**
```python
# Use Free APIs instead of DuckDuckGo
# Option A: Google Custom Search (limited free tier)
# Option B: Bing Search API (Azure required, ~$7/month)
# Option C: Metaphor API (AI-focused search, free tier)
```

### **Option 2: Web Scraping DuckDuckGo (Not Recommended)**
```python
# Violates ToS, prone to breakage
import requests
from bs4 import BeautifulSoup

def search_duckduckgo(query):
    url = f"https://html.duckduckgo.com/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0..."}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Extract results...
```

### **Option 3: Use Tavily Search API (Free Tier)**
```python
# Better alternative specifically for LLM context
pip install tavily-python

from tavily import TavilyClient

client = TavilyClient(api_key="your_key")
results = client.search(
    query="rice disease identification",
    include_answer=True
)
# Returns: [{"title": "...", "url": "...", "content": "..."}, ...]
```

**What I Recommend:** Add a **web search button** to copilot that uses **Tavily** (free tier) to fetch recent agriculture news/research for context.

---

## 📸 **ML Routes for Image Diagnosis**

### **YES, it's still there!** ✅

**Location:** `backend/api/ml_routes.py`

**Current Status:**
- ✅ Endpoint exists: `POST /api/diagnose`
- ✅ Accepts image upload
- ✅ Saves file to `backend/uploads/`
- ⚠️ Returns **placeholder** responses (random diseases)
- ❌ No actual ML model integrated yet

**To Add Real ML Model:**

### **Step 1: Create ML Model Script**

Create `backend/ml_models/disease_classifier.py`:

```python
import torch
from torchvision import transforms, models
from PIL import Image
import json

# Load pre-trained model (e.g., ResNet50 trained on plant diseases)
model = models.resnet50(pretrained=True)
# Finetune on your disease dataset

class PlantDiseaseClassifier:
    def __init__(self, model_path):
        self.model = torch.load(model_path)
        self.model.eval()
        self.diseases = {
            0: "Healthy Leaf",
            1: "Leaf Blast",
            2: "Brown Spot",
            3: "Sheath Blight",
            4: "Nitrogen Deficiency",
            5: "Phosphorus Deficiency"
        }
        
    def predict(self, image_path):
        image = Image.open(image_path).convert('RGB')
        image_tensor = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229
```


## License: unknown
https://github.com/aditya-283/pufferfish-clone/blob/b4e94a22fd8a4f859528afb655732a0b082358df/models/transfer.py

```
Now I'll address all three of your questions:

---

## 🎨 **Frontend Display of 4 Forecasters**

The frontend **currently doesn't display** the 4 forecasters I built. It's showing older data (weather, soil, market, NDVI).

### **Current Frontend Shows:**
```
Temperature  |  Soil Fertility  |  Market Price  |  Confidence
```

### **What Should Be Added:**

Create a new `analytics` or `forecasts` tab showing:

```
┌─────────────────────────────────────────────────────────┐
│ FORECASTS & FACTORS                                     │
├─────────────────────────────────────────────────────────┤
│ 1. YIELD FORECAST                                       │
│    Expected: 3200 kg/ha (±200)  [73% confidence]       │
│    ├─ Soil suitability factor: 0.85                     │
│    ├─ Growing degree days: 1450°C                       │
│    ├─ Drought stress factor: 0.92                       │
│    └─ pH factor: 0.88                                   │
│                                                         │
│ 2. WATER STRESS                                         │
│    Current stress: 0.62 (moderate)  [81% confidence]   │
│    ├─ Rainfall forecast: 45mm next 7 days              │
│    ├─ ET requirement: 4.2mm/day                         │
│    ├─ Soil moisture: 62% of capacity                    │
│    └─ Recommendation: Irrigate 25mm if stress > 0.6    │
│                                                         │
│ 3. DISEASE RISK                                         │
│    Overall risk: 0.45 (low)  [68% confidence]          │
│    ├─ Blast risk: 0.55 (moderate, T: 24°C, RH: 78%)   │
│    ├─ Brown spot: 0.38 (low)                           │
│    ├─ Sheath blight: 0.42 (low)                        │
│    └─ Preventive spray: Tricyclazole if risk > 0.7    │
│                                                         │
│ 4. FERTILIZER NEED                                      │
│    Target yield: 3200 kg/ha                             │
│    ├─ N needed: 85 kg/ha (soil has 12, uptake rate 60) │
│    ├─ P needed: 40 kg/ha (soil has 8, uptake rate 15)  │
│    ├─ K needed: 40 kg/ha (soil has 120, uptake rate 20)│
│    └─ Split: Apply 30% basal, 35% tillering, 35% bloom│
└─────────────────────────────────────────────────────────┘
```

### **Code to Add to Frontend (new component)**

Create `frontend/app/components/ForecastersPanel.js`:

```javascript
export function ForecastersPanel({ forecasts }) {
  if (!forecasts) return null;

  return (
    <div className="dashboard-grid">
      {/* Yield Forecaster */}
      <div className="card">
        <h3>🌾 Yield Forecast</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.yield.estimate} kg/ha</span>
          <span className="metric-range">±{forecasts.yield.ci_range}</span>
          <ConfidenceGauge value={forecasts.yield.confidence * 100} />
        </div>
        <div className="factors">
          <div className="factor">
            <span>Soil Suitability:</span> {forecasts.yield.soil_factor}
          </div>
          <div className="factor">
            <span>Drought Stress:</span> {forecasts.yield.drought_factor}
          </div>
          <div className="factor">
            <span>pH Factor:</span> {forecasts.yield.ph_factor}
          </div>
        </div>
      </div>

      {/* Water Stress Forecaster */}
      <div className="card">
        <h3>💧 Water Stress</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.water_stress.stress_index.toFixed(2)}</span>
          <span className="metric-status">
            {forecasts.water_stress.stress_index < 0.3 ? '🔴 Dry' : 
             forecasts.water_stress.stress_index < 0.6 ? '🟡 Moderate' : '🟢 Wet'}
          </span>
        </div>
        <div className="factors">
          <div>Rainfall: {forecasts.water_stress.rainfall}mm</div>
          <div>ET: {forecasts.water_stress.et}mm</div>
          <div>Soil Moisture: {forecasts.water_stress.soil_moisture}%</div>
        </div>
      </div>

      {/* Disease Risk Forecaster */}
      <div className="card">
        <h3>🦠 Disease Risk</h3>
        <div className="disease-list">
          {forecasts.disease_risks.map(disease => (
            <div key={disease.name} className="disease-item">
              <span>{disease.name}</span>
              <span className={`risk-${disease.severity}`}>
                {(disease.risk * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Fertilizer Recommender */}
      <div className="card">
        <h3>🌱 Fertilizer Need</h3>
        <div className="nutrient-grid">
          <div className="nutrient">
            <span className="nutrient-label">N</span>
            <span className="nutrient-value">{forecasts.fertilizer.n} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">P</span>
            <span className="nutrient-value">{forecasts.fertilizer.p} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">K</span>
            <span className="nutrient-value">{forecasts.fertilizer.k} kg/ha</span>
          </div>
        </div>
        <div className="split-schedule">
          <div>📅 Basal: 30%</div>
          <div>🌱 Tillering: 35%</div>
          <div>🌸 Bloom: 35%</div>
        </div>
      </div>
    </div>
  );
}
```

---

## 🔍 **DuckDuckGo API for Web Search**

DuckDuckGo does **NOT have an official public API**, but there are workarounds:

### **Option 1: Use Existing Alternative (Recommended)**
```python
# Use Free APIs instead of DuckDuckGo
# Option A: Google Custom Search (limited free tier)
# Option B: Bing Search API (Azure required, ~$7/month)
# Option C: Metaphor API (AI-focused search, free tier)
```

### **Option 2: Web Scraping DuckDuckGo (Not Recommended)**
```python
# Violates ToS, prone to breakage
import requests
from bs4 import BeautifulSoup

def search_duckduckgo(query):
    url = f"https://html.duckduckgo.com/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0..."}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Extract results...
```

### **Option 3: Use Tavily Search API (Free Tier)**
```python
# Better alternative specifically for LLM context
pip install tavily-python

from tavily import TavilyClient

client = TavilyClient(api_key="your_key")
results = client.search(
    query="rice disease identification",
    include_answer=True
)
# Returns: [{"title": "...", "url": "...", "content": "..."}, ...]
```

**What I Recommend:** Add a **web search button** to copilot that uses **Tavily** (free tier) to fetch recent agriculture news/research for context.

---

## 📸 **ML Routes for Image Diagnosis**

### **YES, it's still there!** ✅

**Location:** `backend/api/ml_routes.py`

**Current Status:**
- ✅ Endpoint exists: `POST /api/diagnose`
- ✅ Accepts image upload
- ✅ Saves file to `backend/uploads/`
- ⚠️ Returns **placeholder** responses (random diseases)
- ❌ No actual ML model integrated yet

**To Add Real ML Model:**

### **Step 1: Create ML Model Script**

Create `backend/ml_models/disease_classifier.py`:

```python
import torch
from torchvision import transforms, models
from PIL import Image
import json

# Load pre-trained model (e.g., ResNet50 trained on plant diseases)
model = models.resnet50(pretrained=True)
# Finetune on your disease dataset

class PlantDiseaseClassifier:
    def __init__(self, model_path):
        self.model = torch.load(model_path)
        self.model.eval()
        self.diseases = {
            0: "Healthy Leaf",
            1: "Leaf Blast",
            2: "Brown Spot",
            3: "Sheath Blight",
            4: "Nitrogen Deficiency",
            5: "Phosphorus Deficiency"
        }
        
    def predict(self, image_path):
        image = Image.open(image_path).convert('RGB')
        image_tensor = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0
```


## License: unknown
https://github.com/aditya-283/pufferfish-clone/blob/b4e94a22fd8a4f859528afb655732a0b082358df/models/transfer.py

```
Now I'll address all three of your questions:

---

## 🎨 **Frontend Display of 4 Forecasters**

The frontend **currently doesn't display** the 4 forecasters I built. It's showing older data (weather, soil, market, NDVI).

### **Current Frontend Shows:**
```
Temperature  |  Soil Fertility  |  Market Price  |  Confidence
```

### **What Should Be Added:**

Create a new `analytics` or `forecasts` tab showing:

```
┌─────────────────────────────────────────────────────────┐
│ FORECASTS & FACTORS                                     │
├─────────────────────────────────────────────────────────┤
│ 1. YIELD FORECAST                                       │
│    Expected: 3200 kg/ha (±200)  [73% confidence]       │
│    ├─ Soil suitability factor: 0.85                     │
│    ├─ Growing degree days: 1450°C                       │
│    ├─ Drought stress factor: 0.92                       │
│    └─ pH factor: 0.88                                   │
│                                                         │
│ 2. WATER STRESS                                         │
│    Current stress: 0.62 (moderate)  [81% confidence]   │
│    ├─ Rainfall forecast: 45mm next 7 days              │
│    ├─ ET requirement: 4.2mm/day                         │
│    ├─ Soil moisture: 62% of capacity                    │
│    └─ Recommendation: Irrigate 25mm if stress > 0.6    │
│                                                         │
│ 3. DISEASE RISK                                         │
│    Overall risk: 0.45 (low)  [68% confidence]          │
│    ├─ Blast risk: 0.55 (moderate, T: 24°C, RH: 78%)   │
│    ├─ Brown spot: 0.38 (low)                           │
│    ├─ Sheath blight: 0.42 (low)                        │
│    └─ Preventive spray: Tricyclazole if risk > 0.7    │
│                                                         │
│ 4. FERTILIZER NEED                                      │
│    Target yield: 3200 kg/ha                             │
│    ├─ N needed: 85 kg/ha (soil has 12, uptake rate 60) │
│    ├─ P needed: 40 kg/ha (soil has 8, uptake rate 15)  │
│    ├─ K needed: 40 kg/ha (soil has 120, uptake rate 20)│
│    └─ Split: Apply 30% basal, 35% tillering, 35% bloom│
└─────────────────────────────────────────────────────────┘
```

### **Code to Add to Frontend (new component)**

Create `frontend/app/components/ForecastersPanel.js`:

```javascript
export function ForecastersPanel({ forecasts }) {
  if (!forecasts) return null;

  return (
    <div className="dashboard-grid">
      {/* Yield Forecaster */}
      <div className="card">
        <h3>🌾 Yield Forecast</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.yield.estimate} kg/ha</span>
          <span className="metric-range">±{forecasts.yield.ci_range}</span>
          <ConfidenceGauge value={forecasts.yield.confidence * 100} />
        </div>
        <div className="factors">
          <div className="factor">
            <span>Soil Suitability:</span> {forecasts.yield.soil_factor}
          </div>
          <div className="factor">
            <span>Drought Stress:</span> {forecasts.yield.drought_factor}
          </div>
          <div className="factor">
            <span>pH Factor:</span> {forecasts.yield.ph_factor}
          </div>
        </div>
      </div>

      {/* Water Stress Forecaster */}
      <div className="card">
        <h3>💧 Water Stress</h3>
        <div className="forecast-metric">
          <span className="metric-value">{forecasts.water_stress.stress_index.toFixed(2)}</span>
          <span className="metric-status">
            {forecasts.water_stress.stress_index < 0.3 ? '🔴 Dry' : 
             forecasts.water_stress.stress_index < 0.6 ? '🟡 Moderate' : '🟢 Wet'}
          </span>
        </div>
        <div className="factors">
          <div>Rainfall: {forecasts.water_stress.rainfall}mm</div>
          <div>ET: {forecasts.water_stress.et}mm</div>
          <div>Soil Moisture: {forecasts.water_stress.soil_moisture}%</div>
        </div>
      </div>

      {/* Disease Risk Forecaster */}
      <div className="card">
        <h3>🦠 Disease Risk</h3>
        <div className="disease-list">
          {forecasts.disease_risks.map(disease => (
            <div key={disease.name} className="disease-item">
              <span>{disease.name}</span>
              <span className={`risk-${disease.severity}`}>
                {(disease.risk * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Fertilizer Recommender */}
      <div className="card">
        <h3>🌱 Fertilizer Need</h3>
        <div className="nutrient-grid">
          <div className="nutrient">
            <span className="nutrient-label">N</span>
            <span className="nutrient-value">{forecasts.fertilizer.n} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">P</span>
            <span className="nutrient-value">{forecasts.fertilizer.p} kg/ha</span>
          </div>
          <div className="nutrient">
            <span className="nutrient-label">K</span>
            <span className="nutrient-value">{forecasts.fertilizer.k} kg/ha</span>
          </div>
        </div>
        <div className="split-schedule">
          <div>📅 Basal: 30%</div>
          <div>🌱 Tillering: 35%</div>
          <div>🌸 Bloom: 35%</div>
        </div>
      </div>
    </div>
  );
}
```

---

## 🔍 **DuckDuckGo API for Web Search**

DuckDuckGo does **NOT have an official public API**, but there are workarounds:

### **Option 1: Use Existing Alternative (Recommended)**
```python
# Use Free APIs instead of DuckDuckGo
# Option A: Google Custom Search (limited free tier)
# Option B: Bing Search API (Azure required, ~$7/month)
# Option C: Metaphor API (AI-focused search, free tier)
```

### **Option 2: Web Scraping DuckDuckGo (Not Recommended)**
```python
# Violates ToS, prone to breakage
import requests
from bs4 import BeautifulSoup

def search_duckduckgo(query):
    url = f"https://html.duckduckgo.com/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0..."}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Extract results...
```

### **Option 3: Use Tavily Search API (Free Tier)**
```python
# Better alternative specifically for LLM context
pip install tavily-python

from tavily import TavilyClient

client = TavilyClient(api_key="your_key")
results = client.search(
    query="rice disease identification",
    include_answer=True
)
# Returns: [{"title": "...", "url": "...", "content": "..."}, ...]
```

**What I Recommend:** Add a **web search button** to copilot that uses **Tavily** (free tier) to fetch recent agriculture news/research for context.

---

## 📸 **ML Routes for Image Diagnosis**

### **YES, it's still there!** ✅

**Location:** `backend/api/ml_routes.py`

**Current Status:**
- ✅ Endpoint exists: `POST /api/diagnose`
- ✅ Accepts image upload
- ✅ Saves file to `backend/uploads/`
- ⚠️ Returns **placeholder** responses (random diseases)
- ❌ No actual ML model integrated yet

**To Add Real ML Model:**

### **Step 1: Create ML Model Script**

Create `backend/ml_models/disease_classifier.py`:

```python
import torch
from torchvision import transforms, models
from PIL import Image
import json

# Load pre-trained model (e.g., ResNet50 trained on plant diseases)
model = models.resnet50(pretrained=True)
# Finetune on your disease dataset

class PlantDiseaseClassifier:
    def __init__(self, model_path):
        self.model = torch.load(model_path)
        self.model.eval()
        self.diseases = {
            0: "Healthy Leaf",
            1: "Leaf Blast",
            2: "Brown Spot",
            3: "Sheath Blight",
            4: "Nitrogen Deficiency",
            5: "Phosphorus Deficiency"
        }
        
    def predict(self, image_path):
        image = Image.open(image_path).convert('RGB')
        image_tensor = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])(image
```

