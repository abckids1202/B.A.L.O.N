from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any

from database import repositories as repo
from modules.delivery_risk.features import build_features, factor_text, risk_level
from modules.hub_risk.analyzer import analyze_hub
from modules.fleet.analyzer import analyze_fleet
from modules.maintenance.rules import maintenance_score
from modules.routing.optimizer import optimize_routes
from modules.carbon.calculator import estimate_route_carbon
from modules.decision_engine.engine import sla_alert, hub_alert, route_alert
from modules.loading.analyzer import validate_image, demo_detections
from modules.delivery_risk.runtime_models import predict_delay as runtime_delay, predict_sla as runtime_sla
from modules.providers.demo import provider_status as demo_provider_status
from modules.providers.snapshot import OperationalSnapshotBuilder


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=7))).replace(microsecond=0).isoformat()


def _save_alert(alert: dict | None) -> None:
    if not alert:
        return
    existing = repo.row("SELECT alert_id FROM alerts WHERE alert_id=?", (alert["alert_id"],))
    if existing:
        return
    repo.execute(
        "INSERT INTO alerts(alert_id, alert_type, entity_type, entity_id, severity, title, message, recommendation, evidence_json) VALUES(?,?,?,?,?,?,?,?,?)",
        (alert["alert_id"], alert["alert_type"], alert["entity_type"], alert["entity_id"], alert["severity"], alert["title"], alert["message"], alert["recommendation"], repo.jdump(alert["evidence"])),
    )


def list_shipments() -> list[dict]:
    return repo.rows("SELECT * FROM shipments ORDER BY shipment_id")


def list_vehicles() -> list[dict]:
    return repo.rows("SELECT * FROM vehicles ORDER BY vehicle_id")


def list_hubs() -> list[dict]:
    return repo.rows("SELECT * FROM hubs ORDER BY hub_id")


def operational_snapshot(shipment_id: str) -> dict:
    return OperationalSnapshotBuilder().build(shipment_id).to_dict()


def snapshot(shipment_id: str) -> dict:
    snap = operational_snapshot(shipment_id)
    return {
        "shipment": snap["shipment"],
        "hub": snap["hub"],
        "traffic": snap["traffic"],
        "weather": snap["weather"],
        "gps": snap["gps"],
        "hub_event": snap["hub_event"],
    }


def predict_risk(shipment_id: str) -> dict:
    snap = snapshot(shipment_id)
    features = build_features(snap)
    delay_result = runtime_delay(features)
    delay = delay_result["value"]
    sla_result = runtime_sla(features, delay)
    probability = sla_result["value"]
    level = risk_level(probability)
    factors = factor_text(features, delay)
    model_source = f"{delay_result['source']} + {sla_result['source']}"
    model_version = f"delay:{delay_result['version']}|sla:{sla_result['version']}"
    repo.execute("INSERT INTO delay_predictions(shipment_id,predicted_delay_minutes,model_source,model_version,factors_json) VALUES(?,?,?,?,?)", (shipment_id, delay, delay_result["source"], delay_result["version"], repo.jdump(factors)))
    repo.execute("INSERT INTO sla_predictions(shipment_id,probability,risk_level,model_source,model_version,factors_json) VALUES(?,?,?,?,?,?)", (shipment_id, probability, level, sla_result["source"], sla_result["version"], repo.jdump(factors)))
    _save_alert(sla_alert(shipment_id, probability, level, factors))
    return {
        "shipment_id": shipment_id,
        "snapshot": operational_snapshot(shipment_id),
        "features": features,
        "predicted_delay_minutes": delay,
        "sla_probability": probability,
        "risk_level": level,
        "model_source": model_source,
        "model_version": model_version,
        "fallback_used": delay_result["fallback"] or sla_result["fallback"],
        "main_factors": factors,
    }


def predict_batch() -> list[dict]:
    return [predict_risk(s["shipment_id"]) for s in list_shipments()]


def risk_history(shipment_id: str) -> dict:
    return {
        "delay": repo.rows("SELECT * FROM delay_predictions WHERE shipment_id=? ORDER BY created_at DESC LIMIT 25", (shipment_id,)),
        "sla": repo.rows("SELECT * FROM sla_predictions WHERE shipment_id=? ORDER BY created_at DESC LIMIT 25", (shipment_id,)),
    }


def analyze_loading(shipment_id: str, filename: str, content: bytes) -> dict:
    validate_image(filename, content)
    result = demo_detections(content)
    inspection_id = f"LOAD-{result['image_hash'][:10].upper()}"
    repo.execute(
        "INSERT OR REPLACE INTO loading_inspections(inspection_id,shipment_id,compliance_score,status,warnings_json,detections_json,image_hash,model_source,is_demo) VALUES(?,?,?,?,?,?,?,?,?)",
        (inspection_id, shipment_id, result["compliance_score"], result["status"], repo.jdump(result["warnings"]), repo.jdump(result["detections"]), result["image_hash"], result["model_source"], 1),
    )
    repo.execute("UPDATE shipments SET loading_compliance_score=? WHERE shipment_id=?", (result["compliance_score"], shipment_id))
    return {"inspection_id": inspection_id, "shipment_id": shipment_id, **result}


def loading_history(shipment_id: str) -> list[dict]:
    rows = repo.rows("SELECT * FROM loading_inspections WHERE shipment_id=? ORDER BY created_at DESC", (shipment_id,))
    for r in rows:
        r["warnings"] = repo.jload(r.pop("warnings_json"), [])
        r["detections"] = repo.jload(r.pop("detections_json"), [])
    return rows


def carbon_estimate(payload: dict) -> dict:
    vehicle = repo.row("SELECT * FROM vehicles WHERE vehicle_id=?", (payload["vehicle_id"],))
    shipment = repo.row("SELECT * FROM shipments WHERE shipment_id=?", (payload["shipment_id"],))
    result = estimate_route_carbon(payload["distance_km"], shipment["load_weight_kg"], vehicle["capacity_weight_kg"], vehicle["fuel_efficiency_km_per_liter"], vehicle["fuel_type"])
    repo.execute("INSERT INTO carbon_estimates(shipment_id,route_name,fuel_liter,co2_kg,source,assumptions_json) VALUES(?,?,?,?,?,?)", (payload["shipment_id"], payload.get("route_name", "Ad hoc"), result["fuel_liter"], result["co2_kg"], result["source"], repo.jdump(result["assumptions"])))
    return {"shipment_id": payload["shipment_id"], **result}


def _route_stops(shipment_id: str) -> list[dict]:
    route = repo.row("SELECT * FROM routes WHERE shipment_id=? AND is_current=1", (shipment_id,))
    return repo.jload(route["coordinates_json"])


def optimize(payload: dict) -> dict:
    shipment = repo.row("SELECT * FROM shipments WHERE shipment_id=?", (payload["shipment_id"],))
    vehicle = repo.row("SELECT * FROM vehicles WHERE vehicle_id=?", (payload.get("vehicle_id") or shipment["vehicle_id"],))
    snap = snapshot(payload["shipment_id"])
    latest_risk = repo.row("SELECT probability FROM sla_predictions WHERE shipment_id=? ORDER BY created_at DESC LIMIT 1", (payload["shipment_id"],))
    sla_base = latest_risk["probability"] if latest_risk else predict_risk(payload["shipment_id"])["sla_probability"]
    result = optimize_routes(shipment, vehicle, _route_stops(payload["shipment_id"]), snap["traffic"]["traffic_index"], snap["weather"]["severity_index"], sla_base, payload.get("preset", "balanced_ai"), payload.get("weights"))
    result["matrix_source"] = "Haversine demo matrix"
    result["traffic_source"] = snap["traffic"].get("provider", "DemoTrafficProvider")
    result["weather_source"] = snap["weather"].get("provider", "DemoWeatherProvider")
    result["policy"] = payload.get("preset", "balanced_ai")
    repo.execute("DELETE FROM route_candidates WHERE shipment_id=?", (payload["shipment_id"],))
    for cand in result["candidates"]:
        cid = f"{payload['shipment_id']}-{cand['candidate_name'].upper().replace(' ', '-')}"
        repo.execute("INSERT OR REPLACE INTO route_candidates(candidate_id,shipment_id,candidate_name,metrics_json,sequence_json,coordinates_json,score_history_json,selected) VALUES(?,?,?,?,?,?,?,?)", (cid, payload["shipment_id"], cand["candidate_name"], repo.jdump(cand["metrics"]), repo.jdump(cand["sequence"]), repo.jdump(cand["coordinates"]), repo.jdump(cand["score_history"]), int(cand["candidate_name"] == result["recommended"]["candidate_name"])))
    repo.execute("INSERT INTO route_recommendations(shipment_id,recommended_candidate,explanation,evidence_json) VALUES(?,?,?,?)", (payload["shipment_id"], result["recommended"]["candidate_name"], result["explanation"], repo.jdump(result["recommended"]["metrics"])))
    _save_alert(route_alert(payload["shipment_id"], result["recommended"], result["explanation"]))
    return result


def route_candidates(shipment_id: str) -> list[dict]:
    rows = repo.rows("SELECT * FROM route_candidates WHERE shipment_id=? ORDER BY selected DESC, candidate_name", (shipment_id,))
    for r in rows:
        r["metrics"] = repo.jload(r.pop("metrics_json"), {})
        r["sequence"] = repo.jload(r.pop("sequence_json"), [])
        r["coordinates"] = repo.jload(r.pop("coordinates_json"), [])
        r["score_history"] = repo.jload(r.pop("score_history_json"), [])
    return rows


def analyze_hub_service(hub_id: str) -> dict:
    hub = repo.row("SELECT * FROM hubs WHERE hub_id=?", (hub_id,))
    event = repo.row("SELECT * FROM hub_events WHERE hub_id=? ORDER BY captured_at DESC, id DESC LIMIT 1", (hub_id,))
    result = analyze_hub(event, hub)
    _save_alert(hub_alert(result))
    return result


def all_hub_risk() -> list[dict]:
    return sorted([analyze_hub_service(h["hub_id"]) for h in list_hubs()], key=lambda x: x["congestion_score"], reverse=True)


def hub_history(hub_id: str) -> list[dict]:
    return repo.rows("SELECT * FROM hub_events WHERE hub_id=? ORDER BY captured_at DESC LIMIT 50", (hub_id,))


def fleet_analysis() -> dict:
    return analyze_fleet(list_vehicles(), list_shipments())


def maintenance_analysis(vehicle_id: str) -> dict:
    vehicle = repo.row("SELECT * FROM vehicles WHERE vehicle_id=?", (vehicle_id,))
    breakdowns = repo.rows("SELECT * FROM breakdown_history WHERE vehicle_id=?", (vehicle_id,))
    result = maintenance_score(vehicle, breakdowns)
    repo.execute("INSERT INTO maintenance_predictions(vehicle_id,health_score,risk_level,recommended_checkup_days,source,factors_json) VALUES(?,?,?,?,?,?)", (vehicle_id, result["health_score"], result["risk_level"], result["recommended_checkup_days"], result["source"], repo.jdump(result["factors"])))
    return {"vehicle_id": vehicle_id, **result}


def alerts() -> list[dict]:
    order = "CASE severity WHEN 'Critical' THEN 1 WHEN 'Warning' THEN 2 WHEN 'Watch' THEN 3 ELSE 4 END"
    items = repo.rows(f"SELECT * FROM alerts ORDER BY {order}, created_at DESC")
    for item in items:
        item["evidence"] = repo.jload(item.pop("evidence_json"), {})
    return items


def acknowledge_alert(alert_id: str) -> dict:
    repo.execute("UPDATE alerts SET status='Acknowledged', acknowledged_at=? WHERE alert_id=?", (now_iso(), alert_id))
    return {"alert_id": alert_id, "status": "Acknowledged"}


def simulation_reset() -> dict:
    repo.execute("UPDATE simulation_events SET processed=0")
    repo.execute("INSERT OR REPLACE INTO simulation_state(id,current_step,status,current_timestamp,active_shipment_id) VALUES(1,0,'Paused',?,'SHP-1028')", (now_iso(),))
    return simulation_state()


def simulation_state() -> dict:
    state = repo.row("SELECT * FROM simulation_state WHERE id=1") or {"current_step": 0, "status": "Paused", "active_shipment_id": "SHP-1028"}
    events = repo.rows("SELECT * FROM simulation_events ORDER BY step")
    for e in events:
        e["payload"] = repo.jload(e.pop("payload_json"), {})
    return {"state": state, "events": events, "latest_risk": risk_history(state["active_shipment_id"])["sla"][:1], "alerts": alerts()[:8]}


def simulation_next() -> dict:
    event = repo.row("SELECT * FROM simulation_events WHERE processed=0 ORDER BY step LIMIT 1")
    if not event:
        return {"complete": True, **simulation_state()}
    payload = repo.jload(event["payload_json"], {})
    ts = event["timestamp"]
    if event["event_type"] == "TRAFFIC_UPDATE":
        repo.execute("INSERT INTO traffic_snapshots(route_id,shipment_id,traffic_index,average_speed_kmh,travel_time_multiplier,captured_at) VALUES(?,?,?,?,?,?)", ("ROUTE-JKT-BKS-01", "SHP-1028", payload["traffic_index"], payload["average_speed_kmh"], payload["travel_time_multiplier"], ts))
    elif event["event_type"] == "WEATHER_UPDATE":
        repo.execute("INSERT INTO weather_snapshots(shipment_id,condition,rainfall_mm,temperature_c,severity_index,captured_at) VALUES(?,?,?,?,?,?)", ("SHP-1028", payload["condition"], payload["rainfall_mm"], payload["temperature_c"], payload["severity_index"], ts))
    elif event["event_type"] == "HUB_UPDATE":
        repo.execute("INSERT INTO hub_events(hub_id,shipment_id,arrival_rate_per_hour,departure_rate_per_hour,queue_size,average_dwell_time_min,processing_rate_per_hour,sorting_time_min,loading_time_min,unloading_time_min,workforce_capacity_index,current_delayed_shipments,current_total_shipments,captured_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("HUB-BKS", "SHP-1028", payload["arrival_rate_per_hour"], payload["departure_rate_per_hour"], payload["queue_size"], payload["average_dwell_time_min"], payload["processing_rate_per_hour"], payload["sorting_time_min"], payload["loading_time_min"], payload["unloading_time_min"], payload["workforce_capacity_index"], payload["current_delayed_shipments"], payload["current_total_shipments"], ts))
        analyze_hub_service("HUB-BKS")
    elif event["event_type"] == "GPS_UPDATE":
        repo.execute("INSERT INTO gps_events(shipment_id,vehicle_id,lat,lon,speed_kmh,route_deviation_count,captured_at) VALUES(?,?,?,?,?,?,?)", ("SHP-1028", "VAN-021", payload["lat"], payload["lon"], payload["speed_kmh"], payload["route_deviation_count"], ts))
    repo.execute("UPDATE simulation_events SET processed=1 WHERE event_id=?", (event["event_id"],))
    repo.execute("UPDATE simulation_state SET current_step=?, current_timestamp=? WHERE id=1", (event["step"], ts))
    risk = predict_risk("SHP-1028")
    route = optimize({"shipment_id": "SHP-1028", "preset": "balanced_ai"})
    return {"processed_event": {**event, "payload": payload}, "risk": risk, "route_recommendation": route["recommended"], **simulation_state()}


def simulation_play() -> dict:
    repo.execute("UPDATE simulation_state SET status='Playing' WHERE id=1")
    return simulation_state()


def simulation_pause() -> dict:
    repo.execute("UPDATE simulation_state SET status='Paused' WHERE id=1")
    return simulation_state()


def analytics_summary() -> dict:
    shipments = list_shipments()
    latest = [repo.row("SELECT * FROM sla_predictions WHERE shipment_id=? ORDER BY created_at DESC LIMIT 1", (s["shipment_id"],)) or {"risk_level": "Low", "probability": 0.1} for s in shipments]
    candidates = route_candidates("SHP-1028")
    current = next((c for c in candidates if c["candidate_name"] == "Current"), None)
    best = next((c for c in candidates if c.get("selected")), candidates[0] if candidates else None)
    impact = {}
    if current and best:
        impact = {
            "distance_reduction_km": round(current["metrics"]["distance_km"] - best["metrics"]["distance_km"], 2),
            "fuel_reduction_liter": round(current["metrics"]["fuel_liter"] - best["metrics"]["fuel_liter"], 3),
            "co2_reduction_kg": round(current["metrics"]["co2_kg"] - best["metrics"]["co2_kg"], 3),
            "sla_risk_change": round(current["metrics"]["sla_risk"] - best["metrics"]["sla_risk"], 3),
            "baseline": "Current seeded route versus selected recommendation.",
        }
    return {
        "active_shipments": len([s for s in shipments if s["status"] == "Active"]),
        "risk_distribution": {level: len([r for r in latest if r["risk_level"] == level]) for level in ["Low", "Medium", "High", "Critical"]},
        "predicted_delayed_shipments": len([r for r in latest if r["probability"] >= 0.5]),
        "critical_hub_count": len([h for h in all_hub_risk() if h["risk_level"] == "Critical"]),
        "daily_carbon_estimate_kg": round(sum(c["metrics"]["co2_kg"] for c in candidates), 2) if candidates else 0,
        "fleet_utilization": fleet_analysis(),
        "route_impact": impact,
        "alerts": alerts()[:10],
        "assumptions": "Synthetic demo data, Haversine-derived route distances, deterministic carbon baseline.",
    }


def models() -> list[dict]:
    items = repo.rows("SELECT * FROM model_registry ORDER BY name")
    for item in items:
        item["feature_names"] = repo.jload(item.pop("feature_names_json"), [])
        item["metrics"] = repo.jload(item.pop("metrics_json"), {})
    return items


def executive_summary() -> dict:
    summary = analytics_summary()
    return {
        "title": "LogiSense AI Executive Impact Summary",
        "generated_at": now_iso(),
        "synthetic_disclosure": "Synthetic demo environment. Estimates are prototype calculations.",
        "summary": summary,
    }


def provider_status() -> list[dict]:
    return demo_provider_status()


def data_sources() -> list[dict]:
    return [
        {"domain": "Traffic", "category": "Runtime", "current_provider": "DemoTrafficProvider", "future_provider": "Google Routes or TomTom", "status": "SYNTHETIC DEMO"},
        {"domain": "Weather", "category": "Runtime", "current_provider": "DemoWeatherProvider", "future_provider": "BMKG or OpenWeather", "status": "SYNTHETIC DEMO"},
        {"domain": "GPS", "category": "Runtime", "current_provider": "DemoGPSProvider", "future_provider": "Driver app / IoT tracker", "status": "SYNTHETIC DEMO"},
        {"domain": "Shipment/ERP", "category": "Master + Operational", "current_provider": "DemoShipmentProvider", "future_provider": "ERP connector", "status": "SYNTHETIC DEMO"},
        {"domain": "Hub", "category": "Runtime", "current_provider": "DemoHubProvider", "future_provider": "WMS / hub scan logs", "status": "SYNTHETIC DEMO"},
        {"domain": "B.A.L.O.N predictions", "category": "Derived", "current_provider": "Model registry + rule fallback", "future_provider": "Validated model registry", "status": "DERIVED"},
    ]


def training_data_status() -> dict:
    return {
        "delay": {"rows": 420, "target": "delay_minutes", "split_strategy": "prototype random split; group-aware split documented as next hardening", "status": "synthetic prototype target"},
        "sla": {"rows": 420, "target": "sla_breached", "split_strategy": "prototype stratified split; group-aware split documented as next hardening", "status": "synthetic prototype target"},
        "carbon": {"rows": 420, "target": "co2_kg", "split_strategy": "prototype random split", "status": "synthetic formula-derived target"},
        "yolo": {"images": 0, "target": "package/loading classes", "status": "demo mode; team-collected dataset required"},
    }
