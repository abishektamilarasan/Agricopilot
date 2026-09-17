import requests
import json

payload = {
    "latitude": 11.1271, 
    "longitude": 78.6569, 
    "crop": "rice", 
    "country": "India"
}

try:
    response = requests.post("http://localhost:8000/api/analyze", json=payload, timeout=20)
    print("Status:", response.status_code)
    # print("Response:", json.dumps(response.json(), indent=2)[:500])
    print("Success! Backend is reachable and returning data.")
except Exception as e:
    print("Error:", e)
