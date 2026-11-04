import json
import os
from pydantic import BaseModel
from typing import Optional

class YieldData(BaseModel):
    average_yield_tons_ha: float
    max_potential_yield_tons_ha: float
    notes: str
    source: str = "Government/FAO datasets"

def get_historical_yield(crop: str, country: str = "india", region: str = "tamil_nadu") -> Optional[YieldData]:
    """
    Load historical baseline yield data for a crop.
    """
    crop = crop.lower()
    country = country.lower()
    region = region.lower().replace(" ", "_")

    file_path = os.path.join(os.path.dirname(__file__), "datasets", "india_yields.json")
    
    try:
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, "r") as f:
            data = json.load(f)
            
        crop_data = data.get(country, {}).get(region, {}).get(crop)
        if not crop_data:
            return None
            
        return YieldData(
            average_yield_tons_ha=crop_data["average_yield_tons_ha"],
            max_potential_yield_tons_ha=crop_data["max_potential_yield_tons_ha"],
            notes=crop_data["notes"],
            source=f"historical_dataset_{country}_{region}"
        )
    except Exception as e:
        print(f"[Yield Data] Error loading yield data: {e}")
        return None
