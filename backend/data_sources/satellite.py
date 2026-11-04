import os
import httpx
from datetime import datetime, timedelta
from models.schemas import SatelliteData

AGRO_API_KEY = os.getenv("AGROMONITORING_API_KEY", "")
BASE_URL = "http://api.agromonitoring.com/agro/1.0"

async def fetch_ndvi(lat: float, lon: float) -> SatelliteData:
    """
    Fetch NDVI satellite data from Agromonitoring API.
    To avoid creating new polygons on every request, this uses a simplified approach.
    In a full production environment, polygons would be cached by location.
    """
    if not AGRO_API_KEY:
        return SatelliteData(source="unavailable - no api key")
        
    # 1. Create a 100m x 100m polygon around the point
    offset = 0.001
    polygon_geo = {
        "name": f"Field_{lat}_{lon}",
        "geo_json": {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [lon - offset, lat - offset],
                    [lon - offset, lat + offset],
                    [lon + offset, lat + offset],
                    [lon + offset, lat - offset],
                    [lon - offset, lat - offset]
                ]]
            }
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Create polygon (allow duplicates for same location)
            poly_resp = await client.post(
                f"{BASE_URL}/polygons?appid={AGRO_API_KEY}&duplicated=true", 
                json=polygon_geo
            )
            poly_resp.raise_for_status()
            poly_id = poly_resp.json().get("id")
            
            # Fetch recent NDVI
            end_date = int(datetime.now().timestamp())
            start_date = int((datetime.now() - timedelta(days=30)).timestamp())
            
            ndvi_resp = await client.get(
                f"{BASE_URL}/ndvi/history?polyid={poly_id}&start={start_date}&end={end_date}&appid={AGRO_API_KEY}"
            )
            ndvi_resp.raise_for_status()
            ndvi_data = ndvi_resp.json()
            
            if not ndvi_data:
                return SatelliteData(source="unavailable - no recent imagery")
                
            # Get latest
            latest = ndvi_data[-1] # Usually sorted chronologically
            ndvi = latest.get("data", {}).get("mean")
            image = latest.get("image", {}).get("ndvi")
            cloud = latest.get("cl")
            
            status = "Poor"
            if ndvi and ndvi > 0.6:
                status = "Excellent"
            elif ndvi and ndvi > 0.4:
                status = "Good"
            elif ndvi and ndvi > 0.2:
                status = "Fair"
                
            return SatelliteData(
                current_ndvi=round(ndvi, 2) if ndvi else None,
                health_status=status,
                image_url=image,
                cloud_coverage_pct=cloud,
                source="agromonitoring"
            )
            
    except Exception as e:
        print(f"[Satellite] Error fetching NDVI: {e}")
        return SatelliteData(source="unavailable - error")
