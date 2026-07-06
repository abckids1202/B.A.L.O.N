from __future__ import annotations

import os
import requests

API_BASE = os.getenv("LOGISENSE_API_BASE", "http://127.0.0.1:8000")


def _request(method: str, path: str, **kwargs):
    try:
        response = requests.request(method, f"{API_BASE}{path}", timeout=15, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        return {"error": str(exc), "path": path}


def health(): return _request("GET", "/health")
def list_shipments(): return _request("GET", "/api/shipments")
def list_vehicles(): return _request("GET", "/api/vehicles")
def list_hubs(): return _request("GET", "/api/hubs")
def predict_risk(shipment_id): return _request("POST", f"/api/risk/predict/{shipment_id}")
def predict_batch(): return _request("POST", "/api/risk/predict-batch")
def risk_history(shipment_id): return _request("GET", f"/api/risk/history/{shipment_id}")
def optimize_routes(payload): return _request("POST", "/api/routes/optimize", json=payload)
def route_candidates(shipment_id): return _request("GET", f"/api/routes/{shipment_id}/candidates")
def analyze_hub(hub_id): return _request("POST", f"/api/hubs/analyze/{hub_id}")
def hubs_risk(): return _request("GET", "/api/hubs/risk")
def analyze_fleet(): return _request("POST", "/api/fleet/analyze")
def analyze_maintenance(vehicle_id): return _request("POST", f"/api/maintenance/analyze/{vehicle_id}")
def alerts(): return _request("GET", "/api/alerts")
def acknowledge_alert(alert_id): return _request("PATCH", f"/api/alerts/{alert_id}/acknowledge")
def simulation_reset(): return _request("POST", "/api/simulation/reset")
def simulation_next(): return _request("POST", "/api/simulation/next")
def simulation_play(): return _request("POST", "/api/simulation/play")
def simulation_pause(): return _request("POST", "/api/simulation/pause")
def simulation_state(): return _request("GET", "/api/simulation/state")
def analytics_summary(): return _request("GET", "/api/analytics/summary")
def models(): return _request("GET", "/api/models")
def executive_summary(): return _request("GET", "/api/reports/executive-summary")
def analyze_loading(shipment_id, upload):
    return _request("POST", f"/api/loading/analyze?shipment_id={shipment_id}", files={"file": (upload.name, upload.getvalue(), upload.type)})
