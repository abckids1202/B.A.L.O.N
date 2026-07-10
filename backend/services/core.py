from __future__ import annotations

import hashlib
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


INTERVENTION_THRESHOLDS = {
    "min_sla_improvement_pp": 5.0,
    "min_delay_improvement_min": 5.0,
    "min_co2_reduction_percent": 2.0,
}

WIB = timezone(timedelta(hours=7))


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(WIB)


def _iso_dt(value: datetime) -> str:
    return value.astimezone(WIB).replace(microsecond=0).isoformat()


def clock_state() -> dict:
    row = repo.row("SELECT * FROM operational_clock WHERE runtime_id='DEMO-RUNTIME-20260710'")
    if not row:
        now = datetime.now(WIB).replace(microsecond=0)
        return {"runtime_id": "SYSTEM", "timezone": "Asia/Jakarta", "current_demo_time": _iso_dt(now), "status": "SYSTEM", "speed_multiplier": 1, "last_tick_at": _iso_dt(now), "state_version": 0}
    return row


def now_iso() -> str:
    return clock_state()["current_demo_time"]


def forecast_window(shipment: dict, risk: dict, snap: dict | None = None, stage_index: int = 0) -> dict:
    current_time = _parse_dt(now_iso()) or datetime.now(WIB)
    deadline = _parse_dt(shipment.get("sla_deadline")) or (current_time + timedelta(hours=2))
    expected_delay = float(risk.get("predicted_delay_minutes") or 0)
    traffic = float((snap or {}).get("traffic_index") or 0.35)
    weather = float((snap or {}).get("weather_severity") or 0.12)
    hub_excess = max(0, float((snap or {}).get("hub_dwell_excess_min") or 0))
    uncertainty = round(8 + traffic * 14 + weather * 10 + min(20, hub_excess * .18) + max(0, 6 - stage_index), 1)
    low = round(max(0, expected_delay - uncertainty * .55), 1)
    high = round(expected_delay + uncertainty, 1)
    planned_remaining = max(12, float(shipment.get("planned_travel_time_min") or 60) * max(.18, (6 - stage_index) / 6))
    eta_expected = current_time + timedelta(minutes=planned_remaining + expected_delay)
    eta_earliest = current_time + timedelta(minutes=planned_remaining + low)
    eta_latest = current_time + timedelta(minutes=planned_remaining + high)
    next_event_expected = current_time + timedelta(minutes=max(5, min(45, planned_remaining * .32)))
    return {
        "forecast_at": _iso_dt(current_time),
        "delay_low_min": low,
        "delay_expected_min": round(expected_delay, 1),
        "delay_high_min": high,
        "eta_earliest": _iso_dt(eta_earliest),
        "eta_expected": _iso_dt(eta_expected),
        "eta_latest": _iso_dt(eta_latest),
        "expected_next_event_at": _iso_dt(next_event_expected),
        "sla_deadline": _iso_dt(deadline),
        "expected_sla_buffer_min": round((eta_expected - deadline).total_seconds() / -60, 1),
        "best_case_sla_buffer_min": round((eta_earliest - deadline).total_seconds() / -60, 1),
        "worst_case_sla_buffer_min": round((eta_latest - deadline).total_seconds() / -60, 1),
        "methodology": "prototype interval from residual baseline plus traffic, weather, hub dwell, and journey-stage uncertainty",
    }


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


def _paged(sql: str, count_sql: str, params: tuple = (), page: int = 1, page_size: int = 50) -> dict:
    page = max(1, int(page or 1))
    page_size = min(max(1, int(page_size or 50)), 200)
    total = repo.row(count_sql, params)["n"]
    rows = repo.rows(f"{sql} LIMIT ? OFFSET ?", params + (page_size, (page - 1) * page_size))
    return {"items": rows, "page": page, "page_size": page_size, "total": total, "pages": max(1, (total + page_size - 1) // page_size)}


def list_shipments() -> list[dict]:
    return repo.rows("SELECT * FROM shipments ORDER BY shipment_id")


def paged_shipments(page: int = 1, page_size: int = 50, status: str | None = None, q: str | None = None) -> dict:
    clauses = []
    params: list[Any] = []
    if status:
        clauses.append("status=?")
        params.append(status)
    if q:
        clauses.append("(shipment_id LIKE ? OR destination_zone LIKE ? OR vehicle_id LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return _paged(f"SELECT * FROM shipments{where} ORDER BY priority DESC, shipment_id", f"SELECT count(*) AS n FROM shipments{where}", tuple(params), page, page_size)


def list_vehicles() -> list[dict]:
    return repo.rows("SELECT * FROM vehicles ORDER BY vehicle_id")


def paged_vehicles(page: int = 1, page_size: int = 50, status: str | None = None) -> dict:
    where = " WHERE status=?" if status else ""
    params = (status,) if status else ()
    return _paged(f"SELECT * FROM vehicles{where} ORDER BY vehicle_id", f"SELECT count(*) AS n FROM vehicles{where}", params, page, page_size)


def list_hubs() -> list[dict]:
    return repo.rows("SELECT * FROM hubs ORDER BY hub_id")


def list_drivers(page: int = 1, page_size: int = 50) -> dict:
    return _paged("SELECT * FROM drivers ORDER BY driver_id", "SELECT count(*) AS n FROM drivers", (), page, page_size)


def synthetic_network_summary() -> dict:
    run = repo.row("SELECT * FROM synthetic_network_runs ORDER BY created_at DESC LIMIT 1") or {}
    if run:
        run["assumptions"] = repo.jload(run.pop("assumptions_json"), {})
    hub_rows = repo.rows("SELECT origin_hub AS hub_id, count(*) AS active_shipments FROM shipments WHERE status='Active' GROUP BY origin_hub ORDER BY active_shipments DESC")
    vehicle_status = repo.rows("SELECT status, count(*) AS count FROM vehicles GROUP BY status")
    traffic = repo.row("SELECT avg(traffic_index) AS avg_traffic, max(traffic_index) AS max_traffic FROM traffic_snapshots") or {}
    return {
        "run": run,
        "counts": {
            "shipments": repo.row("SELECT count(*) AS n FROM shipments")["n"],
            "active_shipments": repo.row("SELECT count(*) AS n FROM shipments WHERE status='Active'")["n"],
            "hubs": repo.row("SELECT count(*) AS n FROM hubs")["n"],
            "vehicles": repo.row("SELECT count(*) AS n FROM vehicles")["n"],
            "drivers": repo.row("SELECT count(*) AS n FROM drivers")["n"],
            "routing_jobs": run.get("routing_job_count") or repo.row("SELECT count(*) AS n FROM route_recommendations")["n"],
            "operational_context_events": run.get("operational_event_count") or sum((repo.row(f"SELECT count(*) AS n FROM {table}")["n"] for table in ["traffic_snapshots", "weather_snapshots", "gps_events", "hub_events", "simulation_events"])),
        },
        "hub_load": hub_rows,
        "vehicle_status": vehicle_status,
        "traffic": traffic,
    }


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




def _severity_from_score(score: float) -> str:
    if score >= 0.82:
        return "Critical"
    if score >= 0.62:
        return "Warning"
    if score >= 0.38:
        return "Watch"
    return "Info"


def _status_from_severity(severity: str) -> str:
    return "ACTION_REQUIRED" if severity in {"Critical", "Warning"} else "OBSERVED"


def _signal_row(row: dict) -> dict:
    item = dict(row)
    item["normalized_payload"] = repo.jload(item.pop("normalized_payload_json"), {})
    item["state_change"] = repo.jload(item.pop("state_change_json"), {})
    return item


def _latest_signal(signal_type: str, entity_id: str) -> dict | None:
    row = repo.row(
        "SELECT * FROM operational_signals WHERE signal_type=? AND entity_id=? ORDER BY created_at DESC LIMIT 1",
        (signal_type, entity_id),
    )
    return _signal_row(row) if row else None


def list_operational_signals(entity_id: str | None = None, signal_type: str | None = None, limit: int = 80) -> list[dict]:
    clauses = []
    params: list[Any] = []
    if entity_id:
        clauses.append("(entity_id=? OR shipment_id=? OR hub_id=?)")
        params.extend([entity_id, entity_id, entity_id])
    if signal_type:
        clauses.append("signal_type=?")
        params.append(signal_type)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    rows = repo.rows(f"SELECT * FROM operational_signals{where} ORDER BY created_at DESC LIMIT ?", tuple(params + [limit]))
    return [_signal_row(row) for row in rows]


def _persist_signal(
    signal_type: str,
    source_module: str,
    entity_type: str,
    entity_id: str,
    severity: str,
    confidence: float,
    payload: dict,
    state_change: dict,
    model_source: str,
    shipment_id: str | None = None,
    hub_id: str | None = None,
) -> dict:
    payload_hash = hashlib.sha1(repo.jdump(payload).encode("utf-8")).hexdigest()[:10].upper()
    signal_id = f"SIG-{signal_type}-{entity_id}-{payload_hash}".replace(" ", "-")
    repo.execute(
        "INSERT OR REPLACE INTO operational_signals(signal_id,signal_type,source_module,entity_type,entity_id,shipment_id,hub_id,severity,confidence,status,normalized_payload_json,state_change_json,model_source,is_demo) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
        (
            signal_id,
            signal_type,
            source_module,
            entity_type,
            entity_id,
            shipment_id,
            hub_id,
            severity,
            round(confidence, 3),
            _status_from_severity(severity),
            repo.jdump(payload),
            repo.jdump(state_change),
            model_source,
        ),
    )
    return _latest_signal(signal_type, entity_id) or {"signal_id": signal_id}


def _create_signal_intervention(
    signal: dict,
    intervention_type: str,
    action: str,
    reason: str,
    primary_factor: str,
    expected_after: dict,
) -> dict | None:
    if signal["severity"] not in {"Critical", "Warning"}:
        return None
    intervention_id = f"INT-{signal['signal_id']}-{intervention_type}".replace(" ", "-")
    before = signal.get("state_change", {}).get("before", {})
    impact = {
        "expected_delay_change_min": expected_after.get("expected_delay_change_min", 0),
        "actual_reforecast_delay_change_min": expected_after.get("expected_delay_change_min", 0),
        "expected_sla_change_pp": expected_after.get("expected_sla_change_pp", 0),
        "actual_reforecast_sla_change_pp": expected_after.get("expected_sla_change_pp", 0),
        "expected_co2_change_kg": 0,
        "actual_reforecast_co2_change_kg": 0,
        "status": "PENDING_RESULT",
        "evidence": signal,
    }
    now = now_iso()
    repo.execute(
        "INSERT OR REPLACE INTO operational_interventions(intervention_id,shipment_id,journey_id,journey_leg_id,hub_id,vehicle_id,intervention_type,trigger_type,trigger_event_id,severity,status,recommended_action,recommended_entity_id,reason,primary_factor,evidence_json,before_state_json,expected_after_state_json,actual_after_state_json,decision_policy,accepted_at,executed_at,completed_at,impact_json,is_simulated,scenario_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            intervention_id,
            signal.get("shipment_id"),
            f"JRN-{signal['shipment_id']}" if signal.get("shipment_id") else None,
            None,
            signal.get("hub_id"),
            signal.get("normalized_payload", {}).get("observed_vehicle_id"),
            intervention_type,
            signal["signal_type"],
            signal["signal_id"],
            signal["severity"],
            "PENDING",
            action,
            signal["entity_id"],
            reason,
            primary_factor,
            repo.jdump(signal),
            repo.jdump(before),
            repo.jdump(expected_after),
            None,
            "VISUAL_SIGNAL_DEMO_POLICY_V1",
            None,
            None,
            None,
            repo.jdump(impact),
            1,
            "VISUAL_SIGNAL_INTEGRATION",
        ),
    )
    _persist_impact(intervention_id, signal.get("shipment_id") or signal["entity_id"], impact)
    return get_intervention(intervention_id)


def process_package_damage_signal(shipment_id: str, filename: str = "demo-damage.jpg", content: bytes | None = None) -> dict:
    shipment = repo.row("SELECT * FROM shipments WHERE shipment_id=?", (shipment_id,))
    if not shipment:
        raise ValueError(f"Unknown shipment {shipment_id}")
    raw = content or f"{shipment_id}:damage-demo".encode("utf-8")
    if content:
        validate_image(filename, content)
    digest = hashlib.sha1(raw).hexdigest()
    damage_probability = 0.72 if shipment_id == "SHP-1028" else 0.38 + (int(digest[:2], 16) / 255) * 0.28
    severity = _severity_from_score(damage_probability)
    before_score = float(shipment.get("loading_compliance_score") or 86)
    after_score = max(40, round(before_score - damage_probability * 18, 1))
    repo.execute("UPDATE shipments SET loading_compliance_score=? WHERE shipment_id=?", (after_score, shipment_id))
    payload = {
        "risk_label": "potential_damage_risk",
        "detections": [
            {"class_name": "crushed_box", "confidence": round(damage_probability, 2), "bbox": [0.18, 0.21, 0.47, 0.58]},
            {"class_name": "torn_corner", "confidence": round(max(damage_probability - 0.16, 0.12), 2), "bbox": [0.49, 0.32, 0.67, 0.61]},
        ],
        "prototype_assumption": "Demo engine estimates potential damage risk only; it does not determine liability.",
        "image_hash": digest[:16],
    }
    state_change = {
        "before": {"loading_compliance_score": before_score, "quality_hold": False},
        "after": {"loading_compliance_score": after_score, "quality_hold": severity in {"Critical", "Warning"}},
        "affected_engines": ["Delay prediction", "SLA risk prediction", "Decision Engine", "Package Digital Twin"],
    }
    signal = _persist_signal("PACKAGE_DAMAGE_RISK_DETECTED", "PackageDamagePrototypeEngine", "SHIPMENT", shipment_id, severity, damage_probability, payload, state_change, "PrototypeDamageSignalEngine:v1", shipment_id=shipment_id, hub_id=shipment.get("origin_hub"))
    risk = predict_risk(shipment_id)
    intervention = _create_signal_intervention(
        signal,
        "PACKAGE_INSPECTION",
        "Hold package for visual inspection before dispatch.",
        "Potential package damage risk was detected and lowered the package quality context.",
        "Visual package condition risk",
        {"quality_hold": True, "expected_delay_change_min": 8, "expected_sla_change_pp": 3.0, "inspection_policy": "Manual inspection clears or confirms hold."},
    )
    return {"signal": signal, "risk": risk, "intervention": intervention}


def process_hub_occupancy_signal(hub_id: str, area: str = "sorting", observed_packages: int | None = None, observed_workers: int = 6) -> dict:
    hub = repo.row("SELECT * FROM hubs WHERE hub_id=?", (hub_id,))
    if not hub:
        raise ValueError(f"Unknown hub {hub_id}")
    latest = repo.row("SELECT * FROM hub_events WHERE hub_id=? ORDER BY captured_at DESC, id DESC LIMIT 1", (hub_id,))
    base_queue = int(latest.get("queue_size") if latest else 12)
    packages = observed_packages if observed_packages is not None else base_queue + (24 if hub_id == "HUB-JKT" else 12)
    occupancy_ratio = min(1.0, packages / 52)
    severity = _severity_from_score(occupancy_ratio)
    dwell = round(float(hub["normal_dwell_time_min"]) + occupancy_ratio * 42, 1)
    shipment_id = latest.get("shipment_id") if latest else "SHP-1028"
    repo.execute(
        "INSERT INTO hub_events(hub_id,shipment_id,arrival_rate_per_hour,departure_rate_per_hour,queue_size,average_dwell_time_min,processing_rate_per_hour,sorting_time_min,loading_time_min,unloading_time_min,workforce_capacity_index,current_delayed_shipments,current_total_shipments,captured_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            hub_id,
            shipment_id,
            28 + int(occupancy_ratio * 18),
            max(12, 30 - int(occupancy_ratio * 9)),
            packages,
            dwell,
            max(18, 34 - int(occupancy_ratio * 10)),
            round(24 + occupancy_ratio * 34, 1),
            round(18 + occupancy_ratio * 18, 1),
            round(16 + occupancy_ratio * 14, 1),
            round(max(0.55, 1 - occupancy_ratio * 0.32), 2),
            int(4 + occupancy_ratio * 28),
            int(78 + occupancy_ratio * 30),
            now_iso(),
        ),
    )
    payload = {
        "area": area,
        "observed_packages": packages,
        "observed_workers": observed_workers,
        "occupancy_ratio": round(occupancy_ratio, 3),
        "prototype_assumption": "Visual density is a supplemental congestion signal, not a WMS replacement.",
    }
    state_change = {
        "before": {"queue_size": base_queue, "average_dwell_time_min": latest.get("average_dwell_time_min") if latest else None},
        "after": {"queue_size": packages, "average_dwell_time_min": dwell},
        "affected_engines": ["Hub congestion analysis", "Delay prediction", "Decision Engine", "Hub Operations"],
    }
    signal = _persist_signal("HUB_VISUAL_OCCUPANCY_DETECTED", "HubOccupancyPrototypeEngine", "HUB", hub_id, severity, occupancy_ratio, payload, state_change, "PrototypeHubOccupancyEngine:v1", shipment_id=shipment_id, hub_id=hub_id)
    analysis = analyze_hub_service(hub_id)
    intervention = _create_signal_intervention(
        signal,
        "HUB_CONGESTION_REVIEW",
        "Open overflow lane and rebalance sorting capacity.",
        "Visual occupancy increased queue and dwell context for the hub digital twin.",
        "Visual hub density",
        {"expected_delay_change_min": -12, "expected_sla_change_pp": -4.5, "target_queue_size": max(8, packages - 14)},
    )
    return {"signal": signal, "hub_analysis": analysis, "intervention": intervention}


def forecast_hub_overflow_signal(hub_id: str, horizon_minutes: int = 90) -> dict:
    hub = repo.row("SELECT * FROM hubs WHERE hub_id=?", (hub_id,))
    latest = repo.row("SELECT * FROM hub_events WHERE hub_id=? ORDER BY captured_at DESC, id DESC LIMIT 1", (hub_id,))
    if not hub or not latest:
        raise ValueError(f"No hub context found for {hub_id}")
    growth = max(0, float(latest["arrival_rate_per_hour"]) - float(latest["departure_rate_per_hour"]))
    expected_queue = int(float(latest["queue_size"]) + growth * horizon_minutes / 60)
    pressure = min(1.0, expected_queue / 58 + max(0, float(latest["average_dwell_time_min"]) - float(hub["normal_dwell_time_min"])) / 120)
    severity = _severity_from_score(pressure)
    forecast_id = f"OVF-{hub_id}-{horizon_minutes}-{expected_queue}"
    evidence = {
        "arrival_rate_per_hour": latest["arrival_rate_per_hour"],
        "departure_rate_per_hour": latest["departure_rate_per_hour"],
        "current_queue_size": latest["queue_size"],
        "expected_queue_size": expected_queue,
        "horizon_minutes": horizon_minutes,
    }
    repo.execute(
        "INSERT OR REPLACE INTO hub_overflow_forecasts(forecast_id,hub_id,horizon_minutes,overflow_probability,expected_queue_size,risk_level,evidence_json,model_source) VALUES(?,?,?,?,?,?,?,?)",
        (forecast_id, hub_id, horizon_minutes, round(pressure, 3), expected_queue, severity, repo.jdump(evidence), "PrototypeHubOverflowForecastEngine:v1"),
    )
    payload = {**evidence, "overflow_probability": round(pressure, 3), "prototype_assumption": "Deterministic queue growth forecast for competition demo."}
    state_change = {
        "before": {"queue_size": latest["queue_size"], "risk_level": "Observed"},
        "after": {"expected_queue_size": expected_queue, "overflow_probability": round(pressure, 3), "risk_level": severity},
        "affected_engines": ["Hub congestion analysis", "Decision Engine", "Analytics"],
    }
    signal = _persist_signal("HUB_OVERFLOW_RISK_FORECAST", "HubOverflowPrototypeForecastEngine", "HUB", hub_id, severity, pressure, payload, state_change, "PrototypeHubOverflowForecastEngine:v1", shipment_id=latest.get("shipment_id"), hub_id=hub_id)
    intervention = _create_signal_intervention(
        signal,
        "HUB_OVERFLOW_REVIEW",
        "Pre-stage outbound capacity and slow non-priority inbound release.",
        "Forecasted queue growth indicates possible hub overflow within the demo horizon.",
        "Projected hub queue growth",
        {"expected_delay_change_min": -15, "expected_sla_change_pp": -5.0, "horizon_minutes": horizon_minutes},
    )
    return {"forecast_id": forecast_id, "signal": signal, "intervention": intervention}


def process_wrong_loading_signal(shipment_id: str, observed_vehicle_id: str | None = None) -> dict:
    shipment = repo.row("SELECT * FROM shipments WHERE shipment_id=?", (shipment_id,))
    if not shipment:
        raise ValueError(f"Unknown shipment {shipment_id}")
    planned_vehicle = shipment.get("vehicle_id")
    observed = observed_vehicle_id or ("VAN-044" if planned_vehicle != "VAN-044" else "MTR-002")
    mismatch = observed != planned_vehicle
    confidence = 0.91 if mismatch else 0.18
    severity = "Critical" if mismatch else "Info"
    before_score = float(shipment.get("loading_compliance_score") or 86)
    after_score = max(35, before_score - 24) if mismatch else before_score
    repo.execute("UPDATE shipments SET loading_compliance_score=? WHERE shipment_id=?", (after_score, shipment_id))
    payload = {
        "planned_vehicle_id": planned_vehicle,
        "observed_vehicle_id": observed,
        "mismatch": mismatch,
        "prototype_assumption": "Destination comes from shipment data; vision only validates observed loading context.",
    }
    state_change = {
        "before": {"vehicle_id": planned_vehicle, "loading_compliance_score": before_score},
        "after": {"vehicle_id": planned_vehicle, "observed_vehicle_id": observed, "loading_compliance_score": after_score, "dispatch_blocked": mismatch},
        "affected_engines": ["Package Digital Twin", "Delay prediction", "Decision Engine", "Route Planning"],
    }
    signal = _persist_signal("WRONG_PACKAGE_LOADING_DETECTED", "VisionLoadingValidationEngine", "SHIPMENT", shipment_id, severity, confidence, payload, state_change, "PrototypeLoadingValidationEngine:v1", shipment_id=shipment_id, hub_id=shipment.get("origin_hub"))
    risk = predict_risk(shipment_id)
    intervention = _create_signal_intervention(
        signal,
        "PACKAGE_LOADING_CORRECTION",
        f"Remove {shipment_id} from {observed} and reload to planned vehicle {planned_vehicle}.",
        "Observed loading assignment did not match the shipment plan.",
        "Vehicle assignment mismatch",
        {"dispatch_blocked": True, "expected_delay_change_min": 6, "expected_sla_change_pp": 6.0, "planned_vehicle_id": planned_vehicle},
    )
    return {"signal": signal, "risk": risk, "intervention": intervention}


def run_visual_demo_scenario() -> dict:
    damage = process_package_damage_signal("SHP-1028")
    occupancy = process_hub_occupancy_signal("HUB-JKT")
    overflow = forecast_hub_overflow_signal("HUB-JKT")
    wrong_load = process_wrong_loading_signal("SHP-1028", "VAN-044")
    return {
        "package_damage": damage,
        "hub_occupancy": occupancy,
        "hub_overflow": overflow,
        "wrong_loading": wrong_load,
        "recent_signals": list_operational_signals(limit=12),
    }


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
    result = analyze_fleet(list_vehicles(), list_shipments())
    drivers = {row["assigned_vehicle_id"]: row for row in repo.rows("SELECT * FROM drivers WHERE assigned_vehicle_id IS NOT NULL")}
    for item in result.get("vehicle_usage", []):
        driver = drivers.get(item["vehicle_id"], {})
        vehicle = repo.row("SELECT * FROM vehicles WHERE vehicle_id=?", (item["vehicle_id"],)) or {}
        remaining_km = max(120, 83000 - float(vehicle.get("current_km") or 0))
        daily_rate = max(18, float(item.get("distance_today_km") or 0) * 1.18)
        due_days = max(1, int(remaining_km / daily_rate))
        due_expected = (_parse_dt(now_iso()) or datetime.now(WIB)) + timedelta(days=due_days)
        unit = "kWh/km" if vehicle.get("fuel_type") == "electric" else "km/L"
        efficiency = round(1 / max(float(vehicle.get("fuel_efficiency_km_per_liter") or 18), 1), 3) if vehicle.get("fuel_type") == "electric" else vehicle.get("fuel_efficiency_km_per_liter")
        item.update({
            "driver_name": driver.get("driver_name", "Unassigned"),
            "powertrain": vehicle.get("fuel_type", "unknown"),
            "efficiency_value": efficiency,
            "efficiency_unit": unit,
            "maintenance_forecast": {
                "remaining_km": round(remaining_km, 0),
                "daily_distance_rate_km": round(daily_rate, 1),
                "due_expected": _iso_dt(due_expected),
                "due_low": _iso_dt(due_expected - timedelta(days=1)),
                "due_high": _iso_dt(due_expected + timedelta(days=2)),
                "risk_level": "High" if due_days <= 4 else ("Medium" if due_days <= 10 else "Low"),
            },
        })
    return result


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
    """Reset the canonical SHP-1028 demo to a deterministic baseline."""
    from scripts.generate_demo_data import main as seed_demo

    seed_demo()
    risk = predict_risk("SHP-1028")
    route = optimize({"shipment_id": "SHP-1028", "preset": "balanced_ai"})
    view = package_journey_view("SHP-1028")
    return {
        "processed_event": None,
        "risk": risk,
        "route_recommendation": route["recommended"],
        "journey_view": view,
        **simulation_state(),
    }


def simulation_state() -> dict:
    state = repo.row("SELECT * FROM simulation_state WHERE id=1") or {"current_step": 0, "status": "Paused", "active_shipment_id": "SHP-1028"}
    events = repo.rows("SELECT * FROM simulation_events ORDER BY step")
    for e in events:
        e["payload"] = repo.jload(e.pop("payload_json"), {})
    return {"state": state, "events": events, "latest_risk": risk_history(state["active_shipment_id"])["sla"][:1], "alerts": alerts()[:8], "visual_signals": list_operational_signals(limit=8)}


def simulation_next() -> dict:
    event = repo.row("SELECT * FROM simulation_events WHERE processed=0 ORDER BY step LIMIT 1")
    if not event:
        return {"complete": True, "journey_view": package_journey_view("SHP-1028"), **simulation_state()}
    payload = repo.jload(event["payload_json"], {})
    before_state = _latest_prediction_pair("SHP-1028")
    ts = event["timestamp"]
    event_type = event["event_type"]
    if event_type in {"ORIGIN_DISPATCHED", "HUB_DEPARTED", "LAST_MILE_STARTED"}:
        vehicle_id = payload.get("vehicle_id", "VAN-021")
        repo.execute(
            "INSERT INTO gps_events(shipment_id,vehicle_id,lat,lon,speed_kmh,route_deviation_count,captured_at) VALUES(?,?,?,?,?,?,?)",
            ("SHP-1028", vehicle_id, payload.get("lat", -6.25), payload.get("lon", 106.99), payload.get("speed_kmh", 28), payload.get("route_deviation_count", 0), ts),
        )
    if event_type in {"TRAFFIC_UPDATE", "HUB_DEPARTED"}:
        repo.execute(
            "INSERT INTO traffic_snapshots(route_id,shipment_id,traffic_index,average_speed_kmh,travel_time_multiplier,captured_at) VALUES(?,?,?,?,?,?)",
            ("ROUTE-JKT-BKS-01", "SHP-1028", payload.get("traffic_index", 0.68), payload.get("average_speed_kmh", 24), payload.get("travel_time_multiplier", 1.45), ts),
        )
    if event_type == "WEATHER_UPDATE":
        repo.execute(
            "INSERT INTO weather_snapshots(shipment_id,condition,rainfall_mm,temperature_c,severity_index,captured_at) VALUES(?,?,?,?,?,?)",
            ("SHP-1028", payload["condition"], payload["rainfall_mm"], payload["temperature_c"], payload["severity_index"], ts),
        )
    if event_type in {"HUB_ARRIVED", "HUB_UPDATE", "LOCAL_HUB_ARRIVED"}:
        hub_id = payload.get("hub_id", "HUB-BKS")
        repo.execute(
            "INSERT INTO hub_events(hub_id,shipment_id,arrival_rate_per_hour,departure_rate_per_hour,queue_size,average_dwell_time_min,processing_rate_per_hour,sorting_time_min,loading_time_min,unloading_time_min,workforce_capacity_index,current_delayed_shipments,current_total_shipments,captured_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                hub_id,
                "SHP-1028",
                payload.get("arrival_rate_per_hour", 22),
                payload.get("departure_rate_per_hour", 20),
                payload.get("queue_size", 11),
                payload.get("average_dwell_time_min", 0),
                payload.get("processing_rate_per_hour", 30),
                payload.get("sorting_time_min", 18),
                payload.get("loading_time_min", 16),
                payload.get("unloading_time_min", 12),
                payload.get("workforce_capacity_index", 0.92),
                payload.get("current_delayed_shipments", 4),
                payload.get("current_total_shipments", 80),
                ts,
            ),
        )
        analyze_hub_service(hub_id)
    if event_type == "GPS_UPDATE":
        repo.execute(
            "INSERT INTO gps_events(shipment_id,vehicle_id,lat,lon,speed_kmh,route_deviation_count,captured_at) VALUES(?,?,?,?,?,?,?)",
            ("SHP-1028", payload.get("vehicle_id", "VAN-021"), payload["lat"], payload["lon"], payload["speed_kmh"], payload["route_deviation_count"], ts),
        )
    if event_type == "HUB_ARRIVED":
        process_package_damage_signal("SHP-1028")
    if event_type == "HUB_UPDATE":
        process_hub_occupancy_signal(payload.get("hub_id", "HUB-JKT"))
        forecast_hub_overflow_signal(payload.get("hub_id", "HUB-JKT"))
    if event_type == "LAST_MILE_STARTED":
        process_wrong_loading_signal("SHP-1028", payload.get("vehicle_id", "MTR-002"))
    if event_type == "DELIVERED":
        repo.execute("UPDATE shipments SET status='Delivered' WHERE shipment_id='SHP-1028'")
    repo.execute("UPDATE simulation_events SET processed=1 WHERE event_id=?", (event["event_id"],))
    repo.execute("UPDATE simulation_state SET current_step=?, current_timestamp=? WHERE id=1", (event["step"], ts))
    risk = predict_risk("SHP-1028")
    route = optimize({"shipment_id": "SHP-1028", "preset": "balanced_ai"})
    intervention = maybe_create_route_intervention("SHP-1028", event, risk, route, before_state)
    view = package_journey_view("SHP-1028")
    twin = shipment_digital_twin("SHP-1028")
    return {
        "processed_event": {**event, "payload": payload},
        "risk": risk,
        "route_recommendation": route["recommended"],
        "intervention": intervention,
        "journey_view": view,
        "digital_twin": twin,
        **simulation_state(),
    }


JOURNEY_STAGES = [
    ("ORIGIN_PROCESSING", "Origin", "FC-JKT"),
    ("LINE_HAUL", "Line Haul", "FC-JKT to HUB-JKT"),
    ("MAIN_HUB_PROCESSING", "Main Hub", "HUB-JKT"),
    ("INTER_HUB", "Inter-Hub", "HUB-JKT to HUB-BKS"),
    ("LOCAL_HUB_PROCESSING", "Local Hub", "HUB-BKS"),
    ("LAST_MILE", "Last Mile", "Bekasi Timur"),
    ("DELIVERED", "Buyer", "Bekasi Timur"),
]


def _stage_for_step(step: int) -> tuple[int, str, str, str]:
    if step <= 0:
        index = 0
    elif step == 1:
        index = 1
    elif step in {2, 3}:
        index = 2
    elif step in {4, 5}:
        index = 3
    elif step == 6:
        index = 4
    elif step == 7:
        index = 5
    else:
        index = 6
    stage, label, location = JOURNEY_STAGES[index]
    return index, stage, label, location


def _prediction_row(row: dict | None, kind: str) -> dict | None:
    if not row:
        return None
    factors = repo.jload(row.get("factors_json"), [])
    if kind == "delay":
        return {
            "id": row["id"],
            "predicted_delay_minutes": row["predicted_delay_minutes"],
            "model_source": row["model_source"],
            "model_version": row["model_version"],
            "factors": factors,
            "created_at": row["created_at"],
        }
    return {
        "id": row["id"],
        "sla_probability": row["probability"],
        "sla_level": row["risk_level"],
        "model_source": row["model_source"],
        "model_version": row["model_version"],
        "factors": factors,
        "created_at": row["created_at"],
    }


def _timeline_from_events(shipment_id: str) -> list[dict]:
    events = repo.rows("SELECT * FROM simulation_events ORDER BY step")
    timeline = [
        {
            "event_id": "INITIAL",
            "event_type": "SHIPMENT_CREATED",
            "event_at": events[0]["timestamp"] if events else now_iso(),
            "title": f"{shipment_id} journey initialized",
            "description": "Package journey opened at FC-JKT for same-day delivery to Bekasi Timur.",
            "severity": "Info",
            "processed": True,
        }
    ]
    titles = {
        "ORIGIN_DISPATCHED": "Origin dispatch",
        "HUB_ARRIVED": "Main hub arrival",
        "HUB_UPDATE": "Sorting delay update",
        "HUB_DEPARTED": "Inter-hub departure",
        "WEATHER_UPDATE": "Weather deterioration",
        "LOCAL_HUB_ARRIVED": "Local hub arrival",
        "LAST_MILE_STARTED": "Last-mile started",
        "DELIVERED": "Delivered to buyer",
        "TRAFFIC_UPDATE": "Traffic update",
        "GPS_UPDATE": "GPS update",
    }
    for event in events:
        if not event["processed"]:
            continue
        payload = repo.jload(event["payload_json"], {})
        timeline.append(
            {
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "event_at": event["timestamp"],
                "title": titles.get(event["event_type"], event["event_type"].replace("_", " ").title()),
                "description": payload.get("description") or f"{event['entity_id']} updated the active package journey.",
                "severity": payload.get("severity", "Info"),
                "processed": True,
                "payload": payload,
            }
        )
    return timeline


def package_journey_view(shipment_id: str) -> dict:
    shipment = repo.row("SELECT * FROM shipments WHERE shipment_id=?", (shipment_id,))
    if not shipment:
        raise ValueError(f"Unknown shipment {shipment_id}")
    state = repo.row("SELECT * FROM simulation_state WHERE id=1") or {"current_step": 0, "current_timestamp": now_iso(), "active_shipment_id": shipment_id}
    step = int(state.get("current_step") or 0)
    stage_index, stage, stage_label, location = _stage_for_step(step)
    if shipment.get("status") == "Delivered":
        stage_index, stage, stage_label, location = _stage_for_step(99)
    snap = operational_snapshot(shipment_id)
    latest_delay = _prediction_row(repo.row("SELECT * FROM delay_predictions WHERE shipment_id=? ORDER BY created_at DESC LIMIT 1", (shipment_id,)), "delay")
    latest_sla = _prediction_row(repo.row("SELECT * FROM sla_predictions WHERE shipment_id=? ORDER BY created_at DESC LIMIT 1", (shipment_id,)), "sla")
    risk_history_rows = risk_history(shipment_id)
    route_rows = route_candidates(shipment_id)
    latest_recommendation = repo.row("SELECT * FROM route_recommendations WHERE shipment_id=? ORDER BY created_at DESC LIMIT 1", (shipment_id,))
    recommendation = None
    if latest_recommendation:
        recommendation = {
            "candidate": latest_recommendation["recommended_candidate"],
            "explanation": latest_recommendation["explanation"],
            "evidence": repo.jload(latest_recommendation["evidence_json"], {}),
            "created_at": latest_recommendation["created_at"],
        }
    visual_signals = list_operational_signals(entity_id=shipment_id, limit=20)
    hub_visual_signals = list_operational_signals(entity_id=snap["hub"]["hub_id"], limit=20)
    shipment_alerts = [a for a in alerts() if a["entity_id"] in {shipment_id, shipment.get("origin_hub")}]
    carbon_total = round(sum(c["co2_kg"] for c in repo.rows("SELECT co2_kg FROM carbon_estimates WHERE shipment_id=?", (shipment_id,))), 3)
    if not carbon_total and route_rows:
        carbon_total = round(sum(r["metrics"].get("co2_kg", 0) for r in route_rows), 3)
    forecast = forecast_window(shipment, {
        "predicted_delay_minutes": latest_delay["predicted_delay_minutes"] if latest_delay else 0,
        "sla_probability": latest_sla["sla_probability"] if latest_sla else 0,
        "sla_level": latest_sla["sla_level"] if latest_sla else "Unknown",
    }, {
        "traffic_index": snap["traffic"]["traffic_index"],
        "weather_severity": snap["weather"]["severity_index"],
        "hub_dwell_excess_min": round(snap["hub_event"]["average_dwell_time_min"] - snap["hub"]["normal_dwell_time_min"], 1),
    }, stage_index)
    return {
        "shipment_id": shipment_id,
        "journey_id": f"JRN-{shipment_id}",
        "view_version": step,
        "snapshot_at": state.get("current_timestamp") or now_iso(),
        "clock": clock_state(),
        "environment": {"mode": "demo", "contains_simulated_data": True},
        "current_state": {
            "stage": stage,
            "stage_label": stage_label,
            "status": "DELIVERED" if stage == "DELIVERED" else "IN_PROGRESS",
            "location_type": "BUYER" if stage == "DELIVERED" else ("HUB" if "HUB" in stage else "TRANSPORT"),
            "location_id": location,
            "active_leg_id": None if "HUB" in stage else f"LEG-{shipment_id}-{stage_index:02d}",
            "active_hub_visit_id": f"HVIS-{shipment_id}-{stage_index:02d}" if "HUB" in stage else None,
            "stage_started_at": state.get("current_timestamp") or now_iso(),
            "time_in_stage_min": 0,
            "expected_next_event_at": forecast["expected_next_event_at"],
            "current_demo_time": now_iso(),
            "last_operational_update": state.get("current_timestamp") or now_iso(),
        },
        "shipment": shipment,
        "latest_operational_snapshot": {
            "traffic_index": snap["traffic"]["traffic_index"],
            "weather_severity": snap["weather"]["severity_index"],
            "weather_condition": snap["weather"]["condition"],
            "rainfall_mm": snap["weather"]["rainfall_mm"],
            "gps_speed_kmh": snap["gps"]["speed_kmh"],
            "expected_speed_kmh": snap["traffic"]["average_speed_kmh"],
            "route_deviation": snap["gps"]["route_deviation_count"] > 0,
            "hub_id": snap["hub"]["hub_id"],
            "hub_dwell_time_min": snap["hub_event"]["average_dwell_time_min"],
            "hub_dwell_excess_min": round(snap["hub_event"]["average_dwell_time_min"] - snap["hub"]["normal_dwell_time_min"], 1),
        },
        "latest_risk": {
            "predicted_delay_minutes": latest_delay["predicted_delay_minutes"] if latest_delay else None,
            "sla_probability": latest_sla["sla_probability"] if latest_sla else None,
            "sla_level": latest_sla["sla_level"] if latest_sla else "Unknown",
            "delay_source": latest_delay["model_source"] if latest_delay else None,
            "sla_source": latest_sla["model_source"] if latest_sla else None,
            "factors": latest_sla["factors"] if latest_sla else [],
            "forecast_window": forecast,
            "sla_deadline": forecast["sla_deadline"],
            "expected_sla_buffer_min": forecast["expected_sla_buffer_min"],
            "worst_case_sla_buffer_min": forecast["worst_case_sla_buffer_min"],
        },
        "journey_progress": {
            "stages": [{"key": key, "label": label, "state": "complete" if i < stage_index else ("current" if i == stage_index else "future")} for i, (key, label, _loc) in enumerate(JOURNEY_STAGES)],
            "completed_stages": [key for i, (key, _label, _loc) in enumerate(JOURNEY_STAGES) if i < stage_index],
            "current_stage": stage,
            "future_stages": [key for i, (key, _label, _loc) in enumerate(JOURNEY_STAGES) if i > stage_index],
        },
        "timeline": _timeline_from_events(shipment_id) + [
            {
                "event_id": signal["signal_id"],
                "event_type": signal["signal_type"],
                "event_at": signal["created_at"],
                "title": signal["signal_type"].replace("_", " ").title(),
                "description": signal["state_change"].get("affected_engines", ["Operational state"])[0] + " updated from visual or predictive signal.",
                "severity": signal["severity"],
                "processed": True,
                "payload": signal["normalized_payload"],
            }
            for signal in (visual_signals + hub_visual_signals)[:8]
        ],
        "current_hub_visit": {
            "hub_id": snap["hub"]["hub_id"],
            "dwell_time_min": snap["hub_event"]["average_dwell_time_min"],
            "baseline_dwell_time_min": snap["hub"]["normal_dwell_time_min"],
            "dwell_excess_min": round(snap["hub_event"]["average_dwell_time_min"] - snap["hub"]["normal_dwell_time_min"], 1),
            "sorting_time_min": snap["hub_event"]["sorting_time_min"],
            "loading_time_min": snap["hub_event"]["loading_time_min"],
            "unloading_time_min": snap["hub_event"]["unloading_time_min"],
            "visual_signals": hub_visual_signals[:5],
        },
        "visual_intelligence": {
            "package_signals": visual_signals[:8],
            "hub_signals": hub_visual_signals[:8],
            "latest_damage": _latest_signal("PACKAGE_DAMAGE_RISK_DETECTED", shipment_id),
            "latest_wrong_loading": _latest_signal("WRONG_PACKAGE_LOADING_DETECTED", shipment_id),
            "latest_hub_occupancy": _latest_signal("HUB_VISUAL_OCCUPANCY_DETECTED", snap["hub"]["hub_id"]),
            "latest_overflow": _latest_signal("HUB_OVERFLOW_RISK_FORECAST", snap["hub"]["hub_id"]),
        },
        "risk_history": {
            "delay": [_prediction_row(row, "delay") for row in risk_history_rows["delay"]],
            "sla": [_prediction_row(row, "sla") for row in risk_history_rows["sla"]],
        },
        "carbon_summary": {
            "total_co2_kg": carbon_total,
            "stage_shares": {"line_haul": 0.44, "hub": 0.16, "inter_hub": 0.25, "last_mile": 0.15},
        },
        "route_decisions": route_rows,
        "latest_route_recommendation": recommendation,
        "alerts": shipment_alerts,
        "active_interventions": list_interventions(shipment_id=shipment_id),
        "latest_decision": list_interventions(shipment_id=shipment_id)[0] if list_interventions(shipment_id=shipment_id) else None,
        "decision_activity": list_interventions(shipment_id=shipment_id) or ([recommendation] if recommendation else []),
    }



def _latest_prediction_pair(shipment_id: str) -> dict:
    delay = _prediction_row(repo.row("SELECT * FROM delay_predictions WHERE shipment_id=? ORDER BY created_at DESC LIMIT 1", (shipment_id,)), "delay")
    sla = _prediction_row(repo.row("SELECT * FROM sla_predictions WHERE shipment_id=? ORDER BY created_at DESC LIMIT 1", (shipment_id,)), "sla")
    return {
        "predicted_delay_minutes": delay["predicted_delay_minutes"] if delay else None,
        "sla_probability": sla["sla_probability"] if sla else None,
        "sla_level": sla["sla_level"] if sla else "Unknown",
        "delay_source": delay["model_source"] if delay else None,
        "sla_source": sla["model_source"] if sla else None,
        "factors": sla["factors"] if sla else [],
    }


def _intervention_row(row: dict) -> dict:
    item = dict(row)
    for source, target, default in [
        ("evidence_json", "evidence", {}),
        ("before_state_json", "before_state", {}),
        ("expected_after_state_json", "expected_after_state", {}),
        ("actual_after_state_json", "actual_after_state", None),
        ("impact_json", "impact", None),
    ]:
        item[target] = repo.jload(item.pop(source), default)
    return item


def list_interventions(status: str | None = None, shipment_id: str | None = None) -> list[dict]:
    clauses = []
    params = []
    if status:
        clauses.append("status=?")
        params.append(status)
    if shipment_id:
        clauses.append("shipment_id=?")
        params.append(shipment_id)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    rows = repo.rows(f"SELECT * FROM operational_interventions{where} ORDER BY created_at DESC", tuple(params))
    return [_intervention_row(row) for row in rows]


def get_intervention(intervention_id: str) -> dict:
    row = repo.row("SELECT * FROM operational_interventions WHERE intervention_id=?", (intervention_id,))
    if not row:
        raise ValueError(f"Unknown intervention {intervention_id}")
    return _intervention_row(row)


def _route_materiality(shipment_id: str, route_result: dict, risk: dict, before_state: dict | None) -> dict:
    candidates = route_result.get("candidates", [])
    current = next((c for c in candidates if c["candidate_name"] == "Current"), None)
    recommended = route_result.get("recommended") or next((c for c in candidates if c.get("selected")), None)
    if not current or not recommended:
        return {"material": False, "reason": "Route candidates did not include both current and recommended options."}
    if recommended["candidate_name"] == current["candidate_name"]:
        return {"material": False, "reason": "Current route remains the recommended option."}
    current_metrics = current["metrics"]
    recommended_metrics = recommended["metrics"]
    time_saving = round(current_metrics["estimated_time_min"] - recommended_metrics["estimated_time_min"], 2)
    sla_improvement_pp = round((current_metrics["sla_risk"] - recommended_metrics["sla_risk"]) * 100, 2)
    co2_reduction_kg = round(current_metrics["co2_kg"] - recommended_metrics["co2_kg"], 3)
    co2_reduction_pct = round((co2_reduction_kg / current_metrics["co2_kg"]) * 100, 2) if current_metrics["co2_kg"] else 0
    material = (
        sla_improvement_pp >= INTERVENTION_THRESHOLDS["min_sla_improvement_pp"]
        or time_saving >= INTERVENTION_THRESHOLDS["min_delay_improvement_min"]
        or co2_reduction_pct >= INTERVENTION_THRESHOLDS["min_co2_reduction_percent"]
        or (risk.get("sla_probability") or 0) >= 0.7
    )
    return {
        "material": material,
        "reason": "Route candidate produced material improvement." if material else "No candidate met materiality thresholds.",
        "current": current,
        "recommended": recommended,
        "time_saving_min": time_saving,
        "sla_improvement_pp": sla_improvement_pp,
        "co2_reduction_kg": co2_reduction_kg,
        "co2_reduction_pct": co2_reduction_pct,
        "before_probability": before_state.get("sla_probability") if before_state else None,
        "current_probability": risk.get("sla_probability"),
    }


def _persist_impact(intervention_id: str, shipment_id: str, impact: dict) -> None:
    repo.execute(
        "INSERT OR REPLACE INTO intervention_impacts(impact_id,intervention_id,shipment_id,expected_delay_change_min,actual_reforecast_delay_change_min,expected_sla_change_pp,actual_reforecast_sla_change_pp,expected_co2_change_kg,actual_reforecast_co2_change_kg,status,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            f"IMP-{intervention_id}",
            intervention_id,
            shipment_id,
            impact.get("expected_delay_change_min"),
            impact.get("actual_reforecast_delay_change_min"),
            impact.get("expected_sla_change_pp"),
            impact.get("actual_reforecast_sla_change_pp"),
            impact.get("expected_co2_change_kg"),
            impact.get("actual_reforecast_co2_change_kg"),
            impact.get("status", "PENDING_RESULT"),
            repo.jdump(impact.get("evidence", {})),
        ),
    )


def maybe_create_route_intervention(shipment_id: str, trigger_event: dict | None, risk: dict, route_result: dict, before_state: dict | None) -> dict | None:
    event_type = trigger_event.get("event_type") if trigger_event else "MANUAL"
    if event_type not in {"HUB_UPDATE", "HUB_DEPARTED", "WEATHER_UPDATE", "GPS_UPDATE"}:
        return None
    materiality = _route_materiality(shipment_id, route_result, risk, before_state)
    if not materiality["material"]:
        return None
    event_id = trigger_event["event_id"] if trigger_event else "MANUAL"
    intervention_id = f"INT-{shipment_id}-{event_id}-ROUTE"
    recommended = materiality["recommended"]
    current = materiality["current"]
    expected_after = {
        "route_candidate": recommended["candidate_name"],
        "projected_time_min": recommended["metrics"]["estimated_time_min"],
        "projected_sla_probability": recommended["metrics"]["sla_risk"],
        "projected_co2_kg": recommended["metrics"]["co2_kg"],
    }
    before = {
        "route_candidate": current["candidate_name"],
        "projected_time_min": current["metrics"]["estimated_time_min"],
        "projected_sla_probability": current["metrics"]["sla_risk"],
        "projected_co2_kg": current["metrics"]["co2_kg"],
        "previous_sla_probability": materiality.get("before_probability"),
        "current_sla_probability": materiality.get("current_probability"),
    }
    impact = {
        "expected_delay_change_min": -materiality["time_saving_min"],
        "actual_reforecast_delay_change_min": -materiality["time_saving_min"],
        "expected_sla_change_pp": -materiality["sla_improvement_pp"],
        "actual_reforecast_sla_change_pp": -materiality["sla_improvement_pp"],
        "expected_co2_change_kg": -materiality["co2_reduction_kg"],
        "actual_reforecast_co2_change_kg": -materiality["co2_reduction_kg"],
        "status": "IMPROVED" if materiality["time_saving_min"] > 0 or materiality["sla_improvement_pp"] > 0 else "NO_MATERIAL_CHANGE",
        "evidence": materiality,
    }
    now = now_iso()
    repo.execute(
        "INSERT OR REPLACE INTO operational_interventions(intervention_id,shipment_id,journey_id,journey_leg_id,hub_id,vehicle_id,intervention_type,trigger_type,trigger_event_id,severity,status,recommended_action,recommended_entity_id,reason,primary_factor,evidence_json,before_state_json,expected_after_state_json,actual_after_state_json,decision_policy,accepted_at,executed_at,completed_at,impact_json,is_simulated,scenario_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            intervention_id,
            shipment_id,
            f"JRN-{shipment_id}",
            None,
            None,
            None,
            "ROUTE_REOPTIMIZATION",
            "SLA_FORECAST_CHANGE",
            event_id,
            "High" if (risk.get("sla_probability") or 0) >= 0.7 else "Warning",
            "COMPLETED",
            f"Use {recommended['candidate_name']} route candidate.",
            recommended.get("candidate_id") or recommended["candidate_name"],
            f"SLA and route forecast changed materially. {route_result.get('explanation', '')}",
            (risk.get("factors") or ["Route candidate improved the forecast."])[0],
            repo.jdump(materiality),
            repo.jdump(before),
            repo.jdump(expected_after),
            repo.jdump(expected_after),
            "AUTOMATED_DEMO_POLICY_V1",
            now,
            now,
            now,
            repo.jdump(impact),
            1,
            "SHP1028_DELAY_ESCALATION",
        ),
    )
    _persist_impact(intervention_id, shipment_id, impact)
    return get_intervention(intervention_id)


def accept_intervention(intervention_id: str) -> dict:
    now = now_iso()
    repo.execute("UPDATE operational_interventions SET status='COMPLETED', accepted_at=COALESCE(accepted_at,?), executed_at=COALESCE(executed_at,?), completed_at=COALESCE(completed_at,?) WHERE intervention_id=?", (now, now, now, intervention_id))
    return get_intervention(intervention_id)


def reject_intervention(intervention_id: str, reason: str = "Rejected by operator") -> dict:
    repo.execute("UPDATE operational_interventions SET status='REJECTED', rejected_at=?, rejection_reason=? WHERE intervention_id=?", (now_iso(), reason, intervention_id))
    return get_intervention(intervention_id)


def intervention_impact(intervention_id: str) -> dict:
    row = repo.row("SELECT * FROM intervention_impacts WHERE intervention_id=?", (intervention_id,))
    if not row:
        raise ValueError(f"No impact record for {intervention_id}")
    item = dict(row)
    item["evidence"] = repo.jload(item.pop("evidence_json"), {})
    return item


def _digital_twin_sections(view: dict) -> dict:
    shipment = view["shipment"]
    state = view["current_state"]
    snap = view["latest_operational_snapshot"]
    risk = view["latest_risk"]
    stage = state["stage"]
    elapsed = max(0, int(view["view_version"]) * 22)
    completed_stage_count = len(view["journey_progress"]["completed_stages"])
    distance_total = float(shipment.get("route_distance_km") or 0)
    distance_completed = round(min(distance_total, distance_total * completed_stage_count / max(len(JOURNEY_STAGES) - 1, 1)), 2)
    projected_delay = risk["predicted_delay_minutes"] or 0
    projected_total_time = round(float(shipment.get("planned_travel_time_min") or 0) + projected_delay, 1)
    current_is_hub = "HUB" in stage
    delivered = stage == "DELIVERED"
    projected_carbon = view["carbon_summary"]["total_co2_kg"]
    actual_carbon = projected_carbon if delivered else round(projected_carbon * (completed_stage_count / max(len(JOURNEY_STAGES) - 1, 1)), 3)
    forecast = forecast_window(shipment, {"predicted_delay_minutes": projected_delay, "sla_probability": risk["sla_probability"], "sla_level": risk["sla_level"]}, snap, view["view_version"])
    return {
        "shipment_id": view["shipment_id"],
        "journey_id": view["journey_id"],
        "twin_version": view["view_version"],
        "as_of": view["snapshot_at"],
        "clock": clock_state(),
        "actual": {
            "journey_started_at": "2026-07-05T09:00:00+07:00",
            "elapsed_time_min": elapsed,
            "distance_completed_km": distance_completed,
            "accumulated_delay_min": 0 if view["view_version"] <= 1 else round(projected_delay * min(completed_stage_count / 6, 1), 1),
            "carbon_allocated_so_far_kg": actual_carbon,
            "completed_legs": min(completed_stage_count, 3),
            "completed_hub_visits": len([s for s in view["journey_progress"]["completed_stages"] if "HUB" in s]),
            "last_completed_event": view["timeline"][-1]["title"] if view.get("timeline") else None,
            "last_event_time": view["timeline"][-1]["event_at"] if view.get("timeline") else None,
            "final_outcome": {"delivered": delivered, "sla_status": "MET" if delivered and (risk["sla_probability"] or 0) < 0.9 else ("AT_RISK" if not delivered else "REVIEW"), "completed_at": view["timeline"][-1]["event_at"] if delivered and view.get("timeline") else None},
        },
        "current": {
            "stage": stage,
            "stage_label": state["stage_label"],
            "location_type": state["location_type"],
            "location_id": state["location_id"],
            "origin": state["location_id"].split(" to ")[0] if " to " in state["location_id"] else None,
            "destination": state["location_id"].split(" to ")[-1] if " to " in state["location_id"] else shipment.get("destination_zone"),
            "vehicle_id": shipment.get("vehicle_id") if not current_is_hub and not delivered else None,
            "route_id": "ROUTE-JKT-BKS-01" if not current_is_hub and not delivered else None,
            "traffic": {"traffic_index": snap["traffic_index"], "expected_speed_kmh": snap["expected_speed_kmh"]} if not delivered else None,
            "weather": {"condition": snap["weather_condition"], "severity_index": snap["weather_severity"], "rainfall_mm": snap["rainfall_mm"]} if not delivered else None,
            "gps": {"speed_kmh": snap["gps_speed_kmh"], "route_deviation": snap["route_deviation"]} if not current_is_hub and not delivered else None,
            "hub": {
                "hub_id": snap["hub_id"],
                "dwell_time_min": snap["hub_dwell_time_min"],
                "dwell_excess_min": snap["hub_dwell_excess_min"],
            } if current_is_hub else None,
            "current_demo_time": now_iso(),
            "stage_started_at": state.get("stage_started_at") or view["snapshot_at"],
            "time_in_current_stage_min": state.get("time_in_stage_min", 0),
            "last_operational_update": state.get("last_operational_update") or view["snapshot_at"],
        },
        "forecast": {
            "predicted_delay_min": projected_delay,
            "delay_low_min": forecast["delay_low_min"],
            "delay_high_min": forecast["delay_high_min"],
            "eta_earliest": forecast["eta_earliest"],
            "eta_expected": forecast["eta_expected"],
            "eta_latest": forecast["eta_latest"],
            "sla_deadline": forecast["sla_deadline"],
            "expected_sla_buffer_min": forecast["expected_sla_buffer_min"],
            "worst_case_sla_buffer_min": forecast["worst_case_sla_buffer_min"],
            "sla_breach_probability": risk["sla_probability"],
            "sla_level": risk["sla_level"],
            "next_milestone": view["journey_progress"]["future_stages"][0] if view["journey_progress"]["future_stages"] else None,
            "expected_next_event_at": forecast["expected_next_event_at"],
            "expected_next_hub_dwell_min": None if current_is_hub or delivered else 35,
            "main_factors": risk["factors"],
        },
        "projected_final": None if delivered else {
            "earliest_delivery_time": forecast["eta_earliest"],
            "delivery_eta": forecast["eta_expected"],
            "latest_delivery_time": forecast["eta_latest"],
            "estimated_remaining_time_min": round(max(0, (float(shipment.get("planned_travel_time_min") or 0) + projected_delay) * max(.12, (6 - completed_stage_count) / 6)), 1),
            "sla_met_probability": round(1 - (risk["sla_probability"] or 0), 3),
            "projected_total_journey_time_min": projected_total_time,
            "projected_total_delay_min": projected_delay,
            "projected_total_carbon_kg": projected_carbon,
        },
        "active_interventions": list_interventions(shipment_id=view["shipment_id"]),
        "latest_decision": list_interventions(shipment_id=view["shipment_id"])[0] if list_interventions(shipment_id=view["shipment_id"]) else None,
        "quality_context": {
            "loading_compliance_score": shipment.get("loading_compliance_score"),
            "latest_damage_signal": view.get("visual_intelligence", {}).get("latest_damage"),
            "latest_wrong_loading_signal": view.get("visual_intelligence", {}).get("latest_wrong_loading"),
            "active_quality_hold": any(signal.get("severity") in {"Critical", "Warning"} for signal in view.get("visual_intelligence", {}).get("package_signals", [])),
        },
        "visual_intelligence": view.get("visual_intelligence", {}),
        "timeline": view["timeline"],
        "risk_history": view["risk_history"],
        "journey_progress": view["journey_progress"],
    }


def shipment_digital_twin(shipment_id: str) -> dict:
    view = package_journey_view(shipment_id)
    return _digital_twin_sections(view)

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
    visual_signals = list_operational_signals(limit=200)
    network = synthetic_network_summary()
    impact_rows = repo.rows("SELECT * FROM intervention_impacts WHERE status IN ('IMPROVED','COMPLETED','PENDING_RESULT')")
    history = {"interventions_completed": 0, "improved_interventions": 0, "distance_avoided_km": 0, "fuel_avoided_liter": 0, "energy_avoided_kwh": 0, "co2e_avoided_kg": 0, "delay_reduced_min": 0, "avg_sla_risk_change_pp": 0}
    sla_changes = []
    for row in impact_rows:
        evidence = repo.jload(row.get("evidence_json"), {})
        before = evidence.get("before", {})
        after = evidence.get("after", {})
        history["interventions_completed"] += 1
        if row.get("status") == "IMPROVED":
            history["improved_interventions"] += 1
        history["distance_avoided_km"] += max(0, float(before.get("distance_km") or 0) - float(after.get("distance_km") or 0))
        history["fuel_avoided_liter"] += max(0, float(before.get("fuel_liter") or 0) - float(after.get("fuel_liter") or 0))
        history["energy_avoided_kwh"] += max(0, float(before.get("energy_kwh") or 0) - float(after.get("energy_kwh") or 0))
        history["co2e_avoided_kg"] += max(0, float(before.get("co2_kg") or 0) - float(after.get("co2_kg") or 0))
        history["delay_reduced_min"] += max(0, -(float(row.get("actual_reforecast_delay_change_min") or row.get("expected_delay_change_min") or 0)))
        if row.get("actual_reforecast_sla_change_pp") is not None:
            sla_changes.append(float(row["actual_reforecast_sla_change_pp"]))
    for key in ["distance_avoided_km", "fuel_avoided_liter", "energy_avoided_kwh", "co2e_avoided_kg", "delay_reduced_min"]:
        history[key] = round(history[key], 2)
    history["avg_sla_risk_change_pp"] = round(sum(sla_changes) / len(sla_changes), 2) if sla_changes else 0
    history["methodology"] = "Aggregates completed intervention_impacts using positive before-after reductions; SLA is average percentage-point change."
    return {
        "network": network,
        "active_shipments": len([s for s in shipments if s["status"] == "Active"]),
        "risk_distribution": {level: len([r for r in latest if r["risk_level"] == level]) for level in ["Low", "Medium", "High", "Critical"]},
        "predicted_delayed_shipments": len([r for r in latest if r["probability"] >= 0.5]),
        "critical_hub_count": len([h for h in all_hub_risk() if h["risk_level"] == "Critical"]),
        "daily_carbon_estimate_kg": round(sum(c["metrics"]["co2_kg"] for c in candidates), 2) if candidates else 0,
        "fleet_utilization": fleet_analysis(),
        "route_impact": impact,
        "historical_impact": history,
        "operational_history": {
            "completed_route_interventions": [item for item in list_interventions(status="COMPLETED") if item["intervention_type"] == "ROUTE_REOPTIMIZATION"][:12],
            "delivered_shipments": repo.rows("SELECT * FROM shipments WHERE status='Delivered' ORDER BY shipment_id LIMIT 20"),
            "resolved_hub_incidents": repo.rows("SELECT * FROM hub_overflow_forecasts ORDER BY created_at DESC LIMIT 10"),
            "maintenance_reviews": repo.rows("SELECT * FROM maintenance_predictions ORDER BY created_at DESC LIMIT 10"),
        },
        "visual_signal_counts": count_by_signal_type(visual_signals),
        "visual_signal_severity": count_by_signal_severity(visual_signals),
        "latest_visual_signals": visual_signals[:8],
        "alerts": alerts()[:10],
        "assumptions": "Synthetic demo data, Haversine-derived route distances, deterministic carbon baseline.",
    }


def count_by_signal_type(signals: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for signal in signals:
        counts[signal["signal_type"]] = counts.get(signal["signal_type"], 0) + 1
    return counts


def count_by_signal_severity(signals: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for signal in signals:
        counts[signal["severity"]] = counts.get(signal["severity"], 0) + 1
    return counts


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
        {"domain": "Visual package condition", "category": "Runtime signal", "current_provider": "PackageDamagePrototypeEngine", "future_provider": "YOLO damage detector + inspection app", "status": "SYNTHETIC DEMO"},
        {"domain": "Hub visual density", "category": "Runtime signal", "current_provider": "HubOccupancyPrototypeEngine", "future_provider": "CCTV occupancy detector", "status": "SYNTHETIC DEMO"},
        {"domain": "Hub overflow forecast", "category": "Derived", "current_provider": "PrototypeHubOverflowForecastEngine", "future_provider": "Forecast model over WMS + vision + route arrivals", "status": "DERIVED"},
        {"domain": "Loading validation", "category": "Runtime signal", "current_provider": "VisionLoadingValidationEngine", "future_provider": "Dock camera + scan reconciliation", "status": "SYNTHETIC DEMO"},
        {"domain": "B.A.L.O.N predictions", "category": "Derived", "current_provider": "Model registry + rule fallback", "future_provider": "Validated model registry", "status": "DERIVED"},
    ]


def training_data_status() -> dict:
    return {
        "delay": {"rows": 420, "target": "delay_minutes", "split_strategy": "prototype random split; group-aware split documented as next hardening", "status": "synthetic prototype target"},
        "sla": {"rows": 420, "target": "sla_breached", "split_strategy": "prototype stratified split; group-aware split documented as next hardening", "status": "synthetic prototype target"},
        "carbon": {"rows": 420, "target": "co2_kg", "split_strategy": "prototype random split", "status": "synthetic formula-derived target"},
        "package_damage": {"rows": len(list_operational_signals(signal_type="PACKAGE_DAMAGE_RISK_DETECTED")), "target": "potential damage risk", "status": "prototype signal mode; team images required for YOLO training"},
        "hub_occupancy": {"rows": len(list_operational_signals(signal_type="HUB_VISUAL_OCCUPANCY_DETECTED")), "target": "visual occupancy ratio", "status": "prototype signal mode"},
        "hub_overflow": {"rows": len(repo.rows("SELECT forecast_id FROM hub_overflow_forecasts")), "target": "overflow probability", "status": "deterministic forecast prototype"},
        "wrong_loading": {"rows": len(list_operational_signals(signal_type="WRONG_PACKAGE_LOADING_DETECTED")), "target": "planned vs observed loading mismatch", "status": "prototype validation mode"},
        "yolo": {"images": 0, "target": "package/loading classes", "status": "demo mode; team-collected dataset required"},
    }
