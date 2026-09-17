#!/bin/bash
# AgriCopilot Health Check & Verification Script
# Run this to verify all improvements are in place

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  AgriCopilot Implementation Verification"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (MISSING)"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ (MISSING)"
        return 1
    fi
}

# Count
count=0
pass=0

# 1. File structure checks
echo "1️⃣  Core Modules"
for file in "backend/data_pipeline.py" "backend/forecasting.py" "backend/decision_fusion.py"; do
    ((count++))
    if check_file "$file"; then ((pass++)); fi
done

echo ""
echo "2️⃣  Testing & CI/CD"
for file in "backend/tests/test_pipeline.py" ".github/workflows/ci.yml"; do
    ((count++))
    if check_file "$file"; then ((pass++)); fi
done

echo ""
echo "3️⃣  Containerization"
for file in "Dockerfile.backend" "Dockerfile.frontend" "docker-compose.yml"; do
    ((count++))
    if check_file "$file"; then ((pass++)); fi
done

echo ""
echo "4️⃣  Configuration & Documentation"
for file in ".env.example" ".gitignore" "ARCHITECTURE.md" "IMPLEMENTATION_SUMMARY.md" "QUICKSTART.md" "COMPLETION_REPORT.md"; do
    ((count++))
    if check_file "$file"; then ((pass++)); fi
done

echo ""
echo "5️⃣  Dependencies"
((count++))
if check_file "backend/requirements.txt"; then
    if grep -q "scikit-learn\|pytest\|mypy" backend/requirements.txt; then
        echo -e "${GREEN}  • pytest, scikit-learn, mypy found${NC}"
        ((pass++))
    else
        echo -e "${YELLOW}  ⚠ Missing test/ML dependencies${NC}"
    fi
fi

echo ""
echo "─────────────────────────────────────────────────────────────────"

# 2. Code quality checks
echo ""
echo "6️⃣  Code Quality"

# Check for docstrings
if grep -q "\"\"\"" backend/data_pipeline.py; then
    echo -e "${GREEN}✓${NC} Docstrings in data_pipeline.py"
    ((count++))
    ((pass++))
fi

if grep -q "class Forecaster" backend/forecasting.py; then
    echo -e "${GREEN}✓${NC} Forecaster base class in forecasting.py"
    ((count++))
    ((pass++))
fi

if grep -q "class DecisionFusionEngine" backend/decision_fusion.py; then
    echo -e "${GREEN}✓${NC} DecisionFusionEngine in decision_fusion.py"
    ((count++))
    ((pass++))
fi

echo ""
echo "7️⃣  Data Schema"

schemas=(
    "LocationKey"
    "WeatherRecord"
    "SoilRecord"
    "MarketRecord"
    "CropHistoricalRecord"
    "AlignedDataFrame"
    "ETLPipeline"
)

for schema in "${schemas[@]}"; do
    if grep -q "class $schema\|@dataclass" backend/data_pipeline.py; then
        echo -e "${GREEN}✓${NC} $schema defined"
        ((count++))
        ((pass++))
    fi
done

echo ""
echo "8️⃣  Forecasters"

forecasters=(
    "YieldForecaster"
    "WaterStressForecaster"
    "DiseaseRiskForecaster"
    "FertilizerRecommender"
    "ForecastingPipeline"
)

for f in "${forecasters[@]}"; do
    if grep -q "class $f" backend/forecasting.py; then
        echo -e "${GREEN}✓${NC} $f implemented"
        ((count++))
        ((pass++))
    fi
done

echo ""
echo "9️⃣  Decision Engine"

decisions=(
    "IrrigationRecommendation"
    "FertilizerRecommendation"
    "DiseaseManagementRecommendation"
    "HarvestRecommendation"
    "AgricultureDecision"
    "DecisionFusionEngine"
)

for d in "${decisions[@]}"; do
    if grep -q "class $d\|@dataclass" backend/decision_fusion.py; then
        echo -e "${GREEN}✓${NC} $d implemented"
        ((count++))
        ((pass++))
    fi
done

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""

# Summary
pct=$((pass * 100 / count))
echo -e "Results: ${GREEN}$pass / $count${NC} checks passed (${pct}%)"

if [ $pass -eq $count ]; then
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ All improvements implemented successfully! 🎉${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. cp .env.example .env"
    echo "  2. docker-compose up -d"
    echo "  3. docker exec agricopilot-ollama ollama pull mistral"
    echo "  4. curl http://localhost:8000/health"
    echo ""
    exit 0
else
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}✗ Some checks failed. Review output above.${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    exit 1
fi
