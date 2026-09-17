"""Minimal local import check for the backend."""
import asyncio
from config import settings
from data_sources.market import fetch_market

print("Config OK - LLM model:", settings.LLM_MODEL)
market = asyncio.run(fetch_market("rice", "India"))
print("Live market source:", market.source)
