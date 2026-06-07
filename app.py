import json
import math
import os
from fastapi import FastAPI, Request, Response
from typing import List

app = FastAPI()

# 1. Define your exact CORS headers dictionary here
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
}

def calculate_p95(data: List[float]) -> float:
    if not data: return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * 0.95
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    return sorted_data[int(f)] * (c - k) + sorted_data[int(c)] * (k - f)

@app.api_route("/{full_path:path}", methods=["GET", "POST", "OPTIONS"])
async def analyze_latency(request: Request, full_path: str):
    
    # 2. Inject headers into the OPTIONS (Preflight) response
    if request.method == "OPTIONS":
        return Response(headers=CORS_HEADERS)
        
    # 3. Inject headers into the GET (Health check) response
    if request.method == "GET":
        return Response(
            content=json.dumps({"status": "alive"}), 
            media_type="application/json",
            headers=CORS_HEADERS
        )
        
    # 4. Handle the POST request payload
    try:
        payload = await request.json()
        regions = payload.get("regions", [])
        threshold_ms = payload.get("threshold_ms", 0)
    except Exception:
        # Inject headers even if the JSON is bad!
        return Response(
            content=json.dumps({"error": "Invalid JSON format"}), 
            status_code=400, 
            headers=CORS_HEADERS
        )

    file_path = os.path.join(os.path.dirname(__file__), 'telemetry.json')
    try:
        with open(file_path, 'r') as file:
            telemetry = json.load(file)
    except Exception as e:
        # Inject headers if the file fails to load
        return Response(
            content=json.dumps({"error": f"Failed to load telemetry: {e}"}), 
            status_code=500,
            headers=CORS_HEADERS
        )

    results = {}
    for region in regions:
        region_records = [r for r in telemetry if r.get("region") == region]
        latencies = [r.get("latency_ms", 0) for r in region_records]
        uptimes = [r.get("uptime_pct", 0) for r in region_records]
        
        if not latencies:
            results[region] = {"avg_latency": 0, "p95_latency": 0, "avg_uptime": 0, "breaches": 0}
            continue
