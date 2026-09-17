"""
Tamil Nadu Soil Map – Coordinate-based Soil Type Estimation
──────────────────────────────────────────────────────────────
Based on NBSSLUP 1996 soil order map and TNAU soil survey data.

Returns ONLY the soil TYPE (Red, Black, Laterite, Alluvial, etc.)
and its descriptive property RANGES from the survey literature.
We NEVER fabricate specific numeric values (pH, N, P, K, CEC).
Those must come from SoilGrids or a lab test.

Zone polygons are approximated from the NBSSLUP map and
district-level soil survey reports.
"""

from typing import Optional, Dict, Any


# ──────────────────────────────────────────────
# Soil type definitions with RANGE-BASED properties
# from TN Mannvalam & TNAU survey data
# ──────────────────────────────────────────────

TN_SOIL_TYPES: Dict[str, Dict[str, Any]] = {
    "Red Soil": {
        "local_name": "Seemmaṇ (செம்மண்)",
        "usda_order": "Alfisols / Inceptisols",
        "coverage_pct": "~39-62%",
        "texture": "Loamy sand to clay; often coarse",
        "ph_range": "5.5–7.5 (acidic to neutral)",
        "organic_carbon_range": "0.1–0.6%",
        "cec_range": "9–41 cmol(+)/kg",
        "drainage": "Good (except heavy clay spots)",
        "fertility": "Low – N/P deficiency, low OM",
        "major_crops": "Rice, millets, pulses, cotton, sugarcane",
        "constraints": "Erosion-prone, droughty on lighter textures, low N/P/water retention",
        "management": "Add organic manures & balanced NPK; lime acidic spots; terrace slopes; mulch for moisture",
        "description": (
            "Weathered Alfisols formed from granite/gneiss. Deep and loamy to sandy with "
            "subangular-blocky structure. Well-drained on slopes. Typically nutrient-poor "
            "with low organic carbon. Micronutrients (Zn, Cu) often low."
        ),
    },
    "Brown/Laterite Soil": {
        "local_name": "Paḻuppu (பழுப்பு)",
        "usda_order": "Alfisols / Ultisols",
        "coverage_pct": "~38%",
        "texture": "Clayey to gravelly (highly weathered)",
        "ph_range": "4.5–6.5 (acidic)",
        "organic_carbon_range": "<0.2–0.5%",
        "cec_range": "<10 cmol(+)/kg",
        "drainage": "Excellent (free-draining)",
        "fertility": "Extremely low – very low OM, bases leached out",
        "major_crops": "Cashew, tea, coffee, coconut, arecanut, mango",
        "constraints": "Poorly fertile, droughty, excess Fe/Al oxides, Zn/Mn deficient",
        "management": "Enrich with organics (green manures, compost); lime to correct acidity; contour bunding",
        "description": (
            "Highly weathered lateritic soils in hilly/mountainous zones (Western Ghats, Nilgiris). "
            "Gravelly with >35% coarse fragments. Rich in iron oxides (red color) but lack soluble nutrients. "
            "High clay content and pans may cause poor aeration seasonally."
        ),
    },
    "Black Soil": {
        "local_name": "Karuppumaṇ (கருப்புமண்)",
        "usda_order": "Vertisols",
        "coverage_pct": "~12-16%",
        "texture": "Very fine clay (>55-60% clay, smectitic)",
        "ph_range": "7.0–8.5 (neutral to alkaline)",
        "organic_carbon_range": "0.5–1.5%",
        "cec_range": ">50 cmol(+)/kg",
        "drainage": "Poor to moderate (cracks improve drainage when dry)",
        "fertility": "High – very high CEC, abundant K, moderate N/P",
        "major_crops": "Cotton, sorghum, pulses, maize, groundnut, sesame",
        "constraints": "Waterlogging in rainy season, Zn/Fe deficiencies (high pH)",
        "management": "Deep tillage when dry; micronutrient (Zn, Fe) sprays; raised beds for drainage",
        "description": (
            "Deep, self-plowing Vertisols derived from Deccan Trap basalt. Strong shrink-swell behaviour "
            "with deep vertical cracks when dry. Very high water-holding capacity. Naturally fertile "
            "with large nutrient reserves but high pH limits micronutrient availability."
        ),
    },
    "Alluvial/Coastal Soil": {
        "local_name": "Vaṇḍal maṇ (வண்டல் மண்)",
        "usda_order": "Entisols",
        "coverage_pct": "~0.8-7%",
        "texture": "Silty clay (delta) to fine sand (coast)",
        "ph_range": "6.5–8.0 (neutral to slightly alkaline)",
        "organic_carbon_range": "0.2–1.5% (avg ~1.1%)",
        "cec_range": "10–25 cmol(+)/kg",
        "drainage": "Moderate in clay plains; very good in sands",
        "fertility": "Moderate – low N, very low P, moderate K",
        "major_crops": "Rice, sugarcane, banana, legumes; coastal: coconut, casuarina",
        "constraints": "Waterlogging, low N/P, episodic coastal salinity",
        "management": "Drainage control; add N/P fertilizers; gypsum in saline patches",
        "description": (
            "Young river-deposited sediments along rivers and coasts. Very deep (>2m) with "
            "horizontal stratification. The Cauvery delta soils are highly fertile. "
            "Coastal beach soils are infertile and droughty."
        ),
    },
    "Grey/Saline Soil": {
        "local_name": "Saline/Alkali soil",
        "usda_order": "Entisols (saline)",
        "coverage_pct": "~3.5%",
        "texture": "Light-coloured, poor structure",
        "ph_range": "7.5–9.0+ (alkaline)",
        "organic_carbon_range": "Very low",
        "cec_range": "Variable",
        "drainage": "Poor",
        "fertility": "Very low – salt/sodium excess",
        "major_crops": "Salt-tolerant rice, grasses",
        "constraints": "Salinity, waterlogging, sodium excess",
        "management": "Gypsum amendment; organic matter; salt-tolerant varieties",
        "description": (
            "Small pockets in coastal/marine or waterlogged zones. Light-colored with poor "
            "structure and drainage. Cropping is very limited without reclamation."
        ),
    },
    "Mixed Soil": {
        "local_name": "Mixed red-black",
        "usda_order": "Mixed (Alfisols/Vertisols)",
        "coverage_pct": "~2%",
        "texture": "Variable (red-black mosaic)",
        "ph_range": "6.0–8.0",
        "organic_carbon_range": "0.3–1.0%",
        "cec_range": "15–40 cmol(+)/kg",
        "drainage": "Moderate",
        "fertility": "Medium (better than pure red)",
        "major_crops": "Similar to black soil crops where black-dominated",
        "constraints": "Variable – site-specific",
        "management": "Adjusted site-wise based on dominant soil type",
        "description": (
            "Transitional soils with intermingled red and black soil patches. "
            "Minor type occurring along fringes of black soil tracts."
        ),
    },
}


# ──────────────────────────────────────────────
# Zone definitions based on NBSSLUP soil order map
# Each zone is a polygon defined by (lat, lon) vertices.
# Priority: more specific zones checked first.
# ──────────────────────────────────────────────

def _point_in_polygon(lat: float, lon: float, polygon: list[tuple[float, float]]) -> bool:
    """Ray-casting algorithm to check if a point is inside a polygon."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        yi, xi = polygon[i]
        yj, xj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


# Zone polygons: list of (lat, lon) vertices
# Ordered from most specific to least specific (fallback)

_SOIL_ZONES: list[tuple[str, list[tuple[float, float]]]] = [
    # ── VERTISOLS (Black Soil) zones ──
    # Coimbatore-Erode-Salem belt (major black soil concentration)
    ("Black Soil", [
        (11.8, 76.8), (12.2, 77.2), (12.0, 78.2), (11.5, 78.5),
        (11.0, 78.0), (10.8, 77.5), (11.0, 77.0), (11.3, 76.8),
    ]),
    # Madurai-Virudhunagar-Sivagangai scattered Vertisols
    ("Black Soil", [
        (10.2, 77.8), (10.5, 78.0), (10.3, 79.0), (9.8, 79.2),
        (9.5, 78.5), (9.6, 78.0),
    ]),
    # Tirunelveli-Thoothukudi Vertisol pocket
    ("Black Soil", [
        (9.2, 77.5), (9.5, 77.5), (9.5, 78.3), (9.0, 78.3),
        (8.7, 78.0), (8.8, 77.5),
    ]),

    # ── ULTISOLS (Brown/Laterite Soil) zones ──
    # Western Ghats / Nilgiris (major laterite concentration)
    ("Brown/Laterite Soil", [
        (11.8, 76.0), (12.2, 76.5), (11.8, 77.2), (11.2, 77.0),
        (10.5, 77.0), (10.0, 76.8), (10.2, 76.3), (10.8, 76.0),
    ]),
    # Palani Hills / Kodaikanal laterite
    ("Brown/Laterite Soil", [
        (10.5, 77.0), (10.8, 77.3), (10.5, 77.8), (10.0, 77.5),
        (10.0, 77.0),
    ]),
    # Kanyakumari hills laterite
    ("Brown/Laterite Soil", [
        (8.5, 77.0), (8.8, 77.0), (8.8, 77.5), (8.3, 77.5),
        (8.0, 77.3), (8.1, 77.0),
    ]),

    # ── ENTISOLS (Alluvial/Coastal Soil) zones ──
    # Cauvery Delta (Thanjavur, Tiruvarur, Nagapattinam)
    ("Alluvial/Coastal Soil", [
        (11.2, 79.0), (11.5, 79.3), (11.2, 79.8), (10.7, 80.0),
        (10.3, 79.8), (10.5, 79.3), (10.8, 79.0),
    ]),
    # East coast strip (Chennai to Cuddalore)
    ("Alluvial/Coastal Soil", [
        (13.2, 80.0), (13.3, 80.3), (12.5, 80.2), (11.8, 80.0),
        (11.5, 79.8), (11.5, 79.6), (12.0, 79.8), (12.8, 80.0),
    ]),
    # Tamiraparani delta (Tirunelveli coast)
    ("Alluvial/Coastal Soil", [
        (8.5, 77.8), (8.8, 78.0), (8.7, 78.3), (8.3, 78.2),
        (8.1, 78.0),
    ]),

    # ── MOLLISOLS (small patches in south) ──
    ("Mixed Soil", [
        (8.0, 77.0), (8.3, 77.0), (8.5, 77.5), (8.2, 77.8),
        (8.0, 77.5),
    ]),

    # ── Grey/Saline zones (coastal marshes) ──
    # Pulicat/Ennore marshland
    ("Grey/Saline Soil", [
        (13.3, 80.2), (13.5, 80.3), (13.4, 80.4), (13.2, 80.3),
    ]),
    # Pichavaram/Muthupet marshes
    ("Grey/Saline Soil", [
        (10.0, 79.5), (10.3, 79.7), (10.2, 79.9), (9.9, 79.8),
    ]),
]

# TN bounding box
_TN_LAT_MIN = 8.0
_TN_LAT_MAX = 13.6
_TN_LON_MIN = 76.0
_TN_LON_MAX = 80.4


def estimate_soil_type(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Estimate soil type for a coordinate based on the NBSSLUP soil map.

    Returns a dict with soil type name and descriptive properties (ranges),
    or None if the coordinate is outside Tamil Nadu.

    IMPORTANT: This returns ONLY soil TYPE and descriptive ranges.
    It does NOT return specific numeric values (pH, N, CEC, etc.).
    Those must come from SoilGrids API or lab analysis.
    """
    # Check if coordinate is within TN bounds
    if not (_TN_LAT_MIN <= lat <= _TN_LAT_MAX and _TN_LON_MIN <= lon <= _TN_LON_MAX):
        return None

    # Check each zone polygon (most specific first)
    for soil_type_name, polygon in _SOIL_ZONES:
        if _point_in_polygon(lat, lon, polygon):
            soil_info = TN_SOIL_TYPES.get(soil_type_name, {}).copy()
            soil_info["soil_type"] = soil_type_name
            soil_info["estimation_method"] = "NBSSLUP Soil Map (TN)"
            return soil_info

    # Default for TN interior: Red Soil (covers ~62% of TN)
    soil_info = TN_SOIL_TYPES["Red Soil"].copy()
    soil_info["soil_type"] = "Red Soil"
    soil_info["estimation_method"] = "NBSSLUP Soil Map (TN) — default interior"
    return soil_info


def get_soil_type_properties(soil_type: str) -> Optional[Dict[str, Any]]:
    """Get the property ranges for a known soil type name."""
    return TN_SOIL_TYPES.get(soil_type)


def list_soil_types() -> list[str]:
    """Return all known TN soil type names."""
    return list(TN_SOIL_TYPES.keys())
