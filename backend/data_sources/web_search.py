"""
Web Search Integration for AgriCopilot
Uses Tavily API (free tier) for agricultural web search results
"""

import httpx
import os
from typing import List, Dict, Optional
import json
from dotenv import load_dotenv

load_dotenv()

# Using Tavily API (better for LLM context than DuckDuckGo)
# Free tier: 500 calls/month
# Sign up: https://tavily.com

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "tvly-YOUR_API_KEY_HERE")

class WebSearcher:
    """Web search integration for agricultural queries"""
    
    def __init__(self, api_key: str = TAVILY_API_KEY):
        self.api_key = api_key
        self.base_url = "https://api.tavily.com/search"
    
    async def search(
        self, 
        query: str, 
        topic: str = "agriculture",
        max_results: int = 5
    ) -> Dict:
        """
        Search web for agricultural information
        
        Args:
            query: Search query from farmer
            topic: Search topic filter (agriculture, weather, disease, etc.)
            max_results: Number of results to return
            
        Returns:
            Dict with search results and AI summary
        """
        
        # Skip search if no API key
        if not self.api_key or self.api_key == "tvly-YOUR_API_KEY_HERE":
            return {
                "status": "api_not_configured",
                "results": [],
                "summary": None,
                "message": "Web search API not configured. Set TAVILY_API_KEY in .env"
            }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    self.base_url,
                    json={
                        "api_key": self.api_key,
                        "query": f"{query} {topic}",
                        "include_answer": True,
                        "max_results": max_results,
                        "search_depth": "basic"
                    }
                )
                
                if response.status_code != 200:
                    return {
                        "status": "error",
                        "error": f"Tavily API error: {response.status_code}",
                        "results": [],
                        "summary": None
                    }
                
                data = response.json()
                
                return {
                    "status": "success",
                    "results": data.get("results", []),
                    "summary": data.get("answer", ""),
                    "query": query
                }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "results": [],
                "summary": None
            }
    
    async def search_disease(self, disease_name: str, crop: str) -> Dict:
        """Search for disease-specific information"""
        query = f"{disease_name} in {crop} management treatment control"
        return await self.search(query, topic="agriculture")
    
    async def search_weather_impact(self, crop: str, region: str) -> Dict:
        """Search for weather impact on crops"""
        query = f"{crop} cultivation weather impact {region} management"
        return await self.search(query, topic="weather")
    
    async def search_market_price(self, crop: str, country: str = "India") -> Dict:
        """Search for market prices"""
        query = f"{crop} price {country} market today"
        return await self.search(query, topic="market")
    
    async def search_fertilizer_guide(self, crop: str, soil_type: str = "") -> Dict:
        """Search for fertilizer recommendations"""
        query = f"{crop} fertilizer dosage application timing {soil_type}".strip()
        return await self.search(query, topic="agriculture")


async def format_search_results_for_llm(search_result: Dict) -> str:
    """
    Format web search results for LLM context
    
    Returns markdown-formatted string ready for prompt injection
    """
    
    if search_result.get("status") != "success":
        return f"Web search failed: {search_result.get('error', 'Unknown error')}"
    
    results = search_result.get("results", [])
    summary = search_result.get("summary", "")
    
    context = "## Web Search Results\n\n"
    
    if summary:
        context += f"**Summary:** {summary}\n\n"
    
    if results:
        context += "**Sources:**\n"
        for i, result in enumerate(results[:5], 1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")[:200]  # First 200 chars
            
            context += f"{i}. **{title}**\n"
            if url:
                context += f"   Source: {url}\n"
            if content:
                context += f"   {content}...\n"
            context += "\n"
    
    return context


# Global searcher instance
searcher = WebSearcher()
