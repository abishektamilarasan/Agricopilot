"""TNAU Agritech cultivation-cost retrieval for supported crop pages."""

import re
import httpx
from models.schemas import CostEstimate

TNAU_COST_SOURCES = {
    "rice": ("https://agritech.tnau.ac.in/expert_system/paddy/riceecosystem.html", "Conventional cultivation"),
    "maize": ("https://agritech.tnau.ac.in/agriculture/agri_costofcultivation_maize2012.html", "2020-2021 total cost"),
    "groundnut": ("https://agritech.tnau.ac.in/agriculture/agri_costofcultivation_groundnut2012.html", "2020-2021 total cost"),
    "tomato": ("https://agritech.tnau.ac.in/horticulture/horti_cost%20of%20cultivation.html", "Annual horticultural crop"),
    "banana": ("https://agritech.tnau.ac.in/expert_system/banana/cultivation.html", "Main crop"),
}


async def fetch_cultivation_cost(crop: str, field_size_ha: float | None = None) -> CostEstimate:
    crop_key = crop.lower()
    source_info = TNAU_COST_SOURCES.get(crop_key)
    if not source_info:
        return CostEstimate(crop=crop, field_size_ha=field_size_ha, note="N/A: a TNAU cost page has not yet been mapped for this crop.")
    url, method = source_info
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", response.text))
        value = _extract_cost(crop_key, text)
        if value is None:
            return CostEstimate(crop=crop, field_size_ha=field_size_ha, source_url=url, note="N/A: the TNAU cost table could not be parsed.")
        return CostEstimate(crop=crop_key, method=method, cost_inr_per_ha=value, field_size_ha=field_size_ha, total_cost_inr=round(value * field_size_ha, 2) if field_size_ha else None, source="TNAU Agritech", source_url=url, note="Published reference cost; not a live input-price quote.")
    except httpx.HTTPError as error:
        print(f"[Cost] TNAU retrieval failed: {error}")
        return CostEstimate(crop=crop, field_size_ha=field_size_ha, source_url=url, note="N/A: TNAU source unavailable.")


def _extract_cost(crop: str, text: str) -> float | None:
    if crop == "rice":
        match = re.search(r"Total\s+([\d,]+)\s+([\d,]+)", text, re.I)
        return _number(match.group(1)) if match else None
    if crop in {"maize", "groundnut"}:
        match = re.search(r"III\.\s*Total Cost\s+([\d,]+)", text, re.I)
        return _number(match.group(1)) if match else None
    if crop == "tomato":
        match = re.search(r"Tomato\s+(?:[\d,]+\s+){6}([\d,]+)", text, re.I)
        return _number(match.group(1)) if match else None
    if crop == "banana":
        match = re.search(r"Cost of cultivation\s*\|?\s*([\d,]+)", text, re.I)
        return _number(match.group(1)) if match else None
    return None


def _number(value: str) -> float:
    return float(value.replace(",", ""))
