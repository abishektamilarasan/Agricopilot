"""Live market-price integration via India's open Agmarknet data API.
No curated prices are returned: unavailable data is represented explicitly.
"""

import os
import httpx
from typing import Optional
from models.schemas import MarketData

DATA_GOV_API_KEY = os.getenv("DATA_GOV_IN_API_KEY", "")
AGMARKNET_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"
COMMODITY_NAMES = {"rice": "Paddy", "maize": "Maize", "millets": "Jowar", "groundnut": "Groundnut", "onion": "Onion", "tomato": "Tomato", "banana": "Banana", "cotton": "Cotton"}


async def fetch_market(crop: str, country: str = "India", manual_price: Optional[float] = None) -> MarketData:
    if manual_price is not None:
        return MarketData(
            crop=crop,
            current_price_inr_quintal=manual_price,
            price_trend="unavailable",
            source="user-provided",
        )

    if country.lower() != "india" or not DATA_GOV_API_KEY:
        return MarketData(crop=crop, source="unavailable")

    commodity = COMMODITY_NAMES.get(crop.lower(), crop.title())
    url = f"https://api.data.gov.in/resource/{AGMARKNET_RESOURCE}"
    params = {"api-key": DATA_GOV_API_KEY, "format": "json", "limit": 1, "filters[commodity]": commodity}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            records = response.json().get("records", [])
        if not records:
            return MarketData(crop=crop, source="unavailable")
        record = records[0]
        modal_price = float(record["modal_price"])
        return MarketData(
            crop=crop,
            current_price_inr_quintal=modal_price,
            price_trend="unavailable",
            source="agmarknet-data.gov.in",
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        # print(f"[Market] Error fetching live market data: {error}")
        return MarketData(crop=crop, source="unavailable")
