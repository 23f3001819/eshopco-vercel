import json
import math
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Enable CORS for POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

# Define the expected incoming JSON payload
class QueryPayload(BaseModel):
    regions: List[str]
    threshold_ms: float

# Helper to calculate the 95th percentile
def calculate_p95(data: List[float]) -> float:
    if not data: return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * 0.95
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    return sorted_data[int(f)] * (c - k) + sorted_data[int(c)] * (k - f)

@app.post("/")
async def analyze_latency(payload: QueryPayload):
    # Load the telemetry bundle
    file_path = os.path.join(os.path.dirname(__file__), 'telemetry.json')
    try:
        with open(file_path, 'r') as file:
            telemetry = json.load(file)
    except Exception as e:
        return {"error": f"Failed to load telemetry data: {e}"}

    results = {}
    
    # Calculate metrics per requested region
    for region in payload.regions:
        region_records = [r for r in telemetry if r.get("region") == region]
        
        # Extract latencies and the updated uptime_pct key
        latencies = [r.get("latency_ms", 0) for r in region_records]
        uptimes = [r.get("uptime_pct", 0) for r in region_records]
        
        if not latencies:
            results[region] = {"avg_latency": 0, "p95_latency": 0, "avg_uptime": 0, "breaches": 0}
            continue

        avg_lat = sum(latencies) / len(latencies)
        p95_lat = calculate_p95(latencies)
        avg_up = sum(uptimes) / len(uptimes)
        breaches = sum(1 for lat in latencies if lat > payload.threshold_ms)

        results[region] = {
            "avg_latency": round(avg_lat, 2),
            "p95_latency": round(p95_lat, 2),
            "avg_uptime": round(avg_up, 4),
            "breaches": breaches
        }
        
    return results