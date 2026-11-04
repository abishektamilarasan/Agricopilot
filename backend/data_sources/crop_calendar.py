from pydantic import BaseModel
from typing import List, Optional, Dict

class CropSeason(BaseModel):
    name: str
    sowing_months: List[str]
    harvesting_months: List[str]

class CropCalendarData(BaseModel):
    crop: str
    seasons: List[CropSeason]
    notes: str
    source: str = "ICAR/FAO Crop Calendars"

# Static crop calendars for Tamil Nadu / South India
_CALENDARS = {
    "rice": {
        "seasons": [
            {
                "name": "Kharif (Kuruvai)",
                "sowing_months": ["June", "July"],
                "harvesting_months": ["September", "October"]
            },
            {
                "name": "Rabi (Samba/Thaladi)",
                "sowing_months": ["August", "September", "October"],
                "harvesting_months": ["January", "February"]
            },
            {
                "name": "Summer (Navarai)",
                "sowing_months": ["December", "January"],
                "harvesting_months": ["April", "May"]
            }
        ],
        "notes": "Rice is grown in three distinct seasons in Tamil Nadu depending on water availability."
    },
    "maize": {
        "seasons": [
            {
                "name": "Kharif",
                "sowing_months": ["June", "July"],
                "harvesting_months": ["September", "October"]
            },
            {
                "name": "Rabi",
                "sowing_months": ["October", "November"],
                "harvesting_months": ["February", "March"]
            }
        ],
        "notes": "Mostly grown under rainfed conditions in Kharif, and irrigated in Rabi."
    },
    "sugarcane": {
        "seasons": [
            {
                "name": "Eksali (Main)",
                "sowing_months": ["December", "January", "February"],
                "harvesting_months": ["December", "January", "February (Next Year)"]
            },
            {
                "name": "Special Season",
                "sowing_months": ["June", "July"],
                "harvesting_months": ["April", "May (Next Year)"]
            }
        ],
        "notes": "Sugarcane is a long-duration crop taking 10-14 months to mature."
    },
    "cotton": {
        "seasons": [
            {
                "name": "Winter Irrigated",
                "sowing_months": ["August", "September"],
                "harvesting_months": ["February", "March"]
            },
            {
                "name": "Summer Irrigated",
                "sowing_months": ["February", "March"],
                "harvesting_months": ["July", "August"]
            }
        ],
        "notes": "Sowing time critical to avoid pest incidence during boll formation."
    }
}

def get_crop_calendar(crop: str, country: str = "india") -> Optional[CropCalendarData]:
    """
    Load static crop calendar data for sowing and harvesting schedules.
    """
    if country.lower() != "india":
        return None
        
    crop_lower = crop.lower()
    if crop_lower not in _CALENDARS:
        return None
        
    data = _CALENDARS[crop_lower]
    
    seasons = [
        CropSeason(
            name=s["name"], 
            sowing_months=s["sowing_months"], 
            harvesting_months=s["harvesting_months"]
        ) for s in data["seasons"]
    ]
    
    return CropCalendarData(
        crop=crop,
        seasons=seasons,
        notes=data["notes"]
    )
