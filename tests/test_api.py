from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from scripts.generate_demo_data import main as seed


@pytest.fixture(scope="module")
def client():
    seed()
    return TestClient(app)


def test_health(client):
    assert client.get("/health").status_code == 200


def test_core_lists(client):
    assert client.get("/api/shipments").json()
    assert client.get("/api/vehicles").json()
    assert client.get("/api/hubs").json()


def test_risk_route_hub_flow(client):
    risk = client.post("/api/risk/predict/SHP-1028").json()
    assert risk["shipment_id"] == "SHP-1028"
    route = client.post("/api/routes/optimize", json={"shipment_id":"SHP-1028","preset":"balanced_ai"}).json()
    assert route["recommended"]["candidate_name"]
    hub = client.post("/api/hubs/analyze/HUB-BKS").json()
    assert "congestion_score" in hub


def test_simulation_next_changes_state(client):
    client.post("/api/simulation/reset")
    result = client.post("/api/simulation/next").json()
    assert result["processed_event"]["event_id"] == "EVT-001"
    assert result["risk"]["shipment_id"] == "SHP-1028"


def test_reports_models_alerts(client):
    assert client.get("/api/reports/executive-summary").json()["title"]
    assert isinstance(client.get("/api/models").json(), list)
    assert isinstance(client.get("/api/alerts").json(), list)


def test_provider_snapshot_training_endpoints(client):
    providers = client.get("/api/providers/status").json()
    assert providers
    assert any(p["domain"] == "Traffic" for p in providers)
    snapshot = client.get("/api/snapshots/SHP-1028/current").json()
    assert snapshot["shipment_id"] == "SHP-1028"
    assert snapshot["traffic"]["provider"] == "DemoTrafficProvider"
    sources = client.get("/api/data-sources").json()
    assert any(s["domain"] == "Traffic" for s in sources)
    training = client.get("/api/training-data/status").json()
    assert training["delay"]["rows"] >= 1


def test_package_journey_view_and_demo_pipeline(client):
    reset = client.post("/api/simulation/reset").json()
    assert reset["journey_view"]["current_state"]["stage"] == "ORIGIN_PROCESSING"
    first = client.post("/api/simulation/next").json()
    assert first["processed_event"]["event_id"] == "EVT-001"
    assert first["journey_view"]["current_state"]["stage"] == "LINE_HAUL"
    second = client.post("/api/simulation/next").json()
    assert second["journey_view"]["current_state"]["stage"] == "MAIN_HUB_PROCESSING"
    view = client.get("/api/packages/SHP-1028/journey-view").json()
    assert view["journey_progress"]["current_stage"] == view["current_state"]["stage"]
    assert view["timeline"]
    assert isinstance(view["risk_history"]["sla"], list)


def test_digital_twin_temporal_sections_and_interventions(client):
    client.post("/api/simulation/reset")
    origin = client.get("/api/packages/SHP-1028/digital-twin").json()
    assert set(["actual", "current", "forecast", "projected_final"]).issubset(origin)
    assert origin["current"]["stage"] == "ORIGIN_PROCESSING"
    assert origin["current"]["hub"] is None
    for _ in range(7):
        client.post("/api/simulation/next")
    twin = client.get("/api/packages/SHP-1028/digital-twin").json()
    assert twin["active_interventions"]
    interventions = client.get("/api/interventions?shipment_id=SHP-1028").json()
    assert interventions
    first = interventions[0]
    assert first["status"] in {"COMPLETED", "PENDING", "ACCEPTED"}
    impact = client.get(f"/api/interventions/{first['intervention_id']}/impact").json()
    assert impact["status"] in {"IMPROVED", "NO_MATERIAL_CHANGE", "PENDING_RESULT"}



def test_visual_operational_signals_integrate_with_twins(client):
    damage = client.post("/api/vision/package-damage?shipment_id=SHP-1028").json()
    assert damage["signal"]["signal_type"] == "PACKAGE_DAMAGE_RISK_DETECTED"
    assert damage["risk"]["shipment_id"] == "SHP-1028"
    loading = client.post("/api/vision/loading-validation?shipment_id=SHP-1028&observed_vehicle_id=VAN-044").json()
    assert loading["signal"]["normalized_payload"]["mismatch"] is True
    occupancy = client.post("/api/vision/hub-occupancy/HUB-JKT").json()
    assert occupancy["signal"]["signal_type"] == "HUB_VISUAL_OCCUPANCY_DETECTED"
    overflow = client.post("/api/forecast/hub-overflow/HUB-JKT").json()
    assert overflow["signal"]["signal_type"] == "HUB_OVERFLOW_RISK_FORECAST"
    signals = client.get("/api/operational-signals?entity_id=SHP-1028").json()
    assert any(signal["signal_type"] == "WRONG_PACKAGE_LOADING_DETECTED" for signal in signals)
    twin = client.get("/api/packages/SHP-1028/digital-twin").json()
    assert twin["quality_context"]["latest_damage_signal"]
    summary = client.get("/api/analytics/summary").json()
    assert summary["visual_signal_counts"]["PACKAGE_DAMAGE_RISK_DETECTED"] >= 1



def test_compact_synthetic_network_scale_and_pagination(client):
    summary = client.get("/api/network/summary").json()
    assert summary["counts"]["shipments"] == 500
    assert summary["counts"]["hubs"] == 12
    assert summary["counts"]["vehicles"] == 60
    assert summary["counts"]["drivers"] == 50
    assert summary["counts"]["routing_jobs"] == 40
    page = client.get("/api/shipments/paged?page=1&page_size=25").json()
    assert page["total"] == 500
    assert len(page["items"]) == 25
    ids = [item["shipment_id"] for item in page["items"]]
    assert len(ids) == len(set(ids))
    drivers = client.get("/api/drivers?page=1&page_size=10").json()
    assert drivers["total"] == 50
    assert len(drivers["items"]) == 10


def test_synthetic_shipments_are_not_stage_clones(client):
    shipments = client.get("/api/shipments/paged?page=1&page_size=100").json()["items"]
    repeated_family_ids = [s["shipment_id"] for s in shipments if s["shipment_id"].count("-") > 1]
    assert not repeated_family_ids
    signatures = {(s["vehicle_id"], s["sla_deadline"], round(s["route_distance_km"], 1), s["destination_zone"]) for s in shipments}
    assert len(signatures) > 85



def test_time_clock_forecast_and_sla_windows(client):
    clock = client.get("/api/clock").json()
    assert clock["timezone"] == "Asia/Jakarta"
    assert clock["current_demo_time"]
    twin = client.get("/api/packages/SHP-1028/digital-twin").json()
    forecast = twin["forecast"]
    eta_earliest = datetime.fromisoformat(forecast["eta_earliest"])
    eta_expected = datetime.fromisoformat(forecast["eta_expected"])
    eta_latest = datetime.fromisoformat(forecast["eta_latest"])
    assert eta_earliest <= eta_expected <= eta_latest
    assert forecast["delay_low_min"] <= forecast["predicted_delay_min"] <= forecast["delay_high_min"]
    assert "expected_sla_buffer_min" in forecast


def test_historical_impact_is_aggregated_from_completed_records(client):
    summary = client.get("/api/analytics/summary").json()
    impact = summary["historical_impact"]
    assert impact["interventions_completed"] >= 24
    assert impact["improved_interventions"] >= 19
    assert impact["distance_avoided_km"] > 0
    assert impact["fuel_avoided_liter"] > 0
    assert impact["energy_avoided_kwh"] > 0
    assert impact["co2e_avoided_kg"] > 0
    assert impact["delay_reduced_min"] > 0
    assert "methodology" in impact


def test_fleet_rows_expose_driver_maintenance_and_power_units(client):
    fleet = client.post("/api/fleet/analyze").json()
    usage = fleet["vehicle_usage"]
    assert any(row["driver_name"] != "Unassigned" for row in usage)
    assert any(row["status"] != "Active" for row in usage)
    assert len({row["active_operating_minutes"] for row in usage}) > 10
    ev_rows = [row for row in usage if row["powertrain"] == "electric"]
    assert ev_rows
    assert all(row["efficiency_unit"] == "kWh/km" for row in ev_rows)
    assert all(row["maintenance_forecast"]["due_low"] <= row["maintenance_forecast"]["due_expected"] <= row["maintenance_forecast"]["due_high"] for row in usage)



def test_marketing_analytics_business_views(client):
    summary = client.get("/api/analytics/summary").json()
    marketing = summary["marketing"]
    assert marketing["top_order_hubs"]
    assert marketing["top_destination_zones"]
    assert marketing["priority_mix"]
    assert marketing["top_priority_drivers"]
    assert marketing["daily_order_trend"]
    assert marketing["hub_revenue_proxy"]
    assert marketing["top_order_hubs"][0]["orders"] > 0
    assert marketing["top_priority_drivers"][0]["business_score"] > 0

def test_visual_intelligence_four_stage_workflows(client):
    assets = client.get("/api/visual-intelligence/assets").json()
    assert assets["wrong_loading_strategy"]["train_new_yolo"] is False
    assert "label" in assets["package_and_label_detector"]["classes"]
    assert "wet" in assets["damage_detector"]["classes"]

    quality = client.post("/api/visual-intelligence/package-quality?shipment_id=SHP-1028").json()
    assert quality["stage"] == "PACKAGE_ARRIVAL_QUALITY_GATE"
    assert quality["signal"]["signal_type"] == "PACKAGE_DAMAGE_RISK_DETECTED"
    assert quality["next_step"] == "QR Scan & Wrong Loading Detection"

    dispatch = client.post("/api/visual-intelligence/dispatch-validation?shipment_id=SHP-1028&observed_vehicle_id=VAN-044").json()
    assert dispatch["train_new_yolo"] is False
    assert dispatch["qr_identity"]["qr_payload"] == "SHP-1028"
    assert dispatch["dispatch_allowed"] is False
    assert dispatch["status"] == "WRONG_LOADING"

    loading = client.post("/api/visual-intelligence/loading-compliance?vehicle_id=TRK-001&loaded_packages=6&visual_capacity=5").json()
    assert loading["stage"] == "LOADING_COMPLIANCE"
    assert loading["dispatch_allowed"] is False
    assert loading["visual_load_utilization_estimate"] > 1

    hub = client.post("/api/visual-intelligence/hub-vision?hub_id=HUB-JKT&observed_packages=42").json()
    assert hub["stage"] == "HUB_CONGESTION_DETECTION"
    assert hub["tracking"]["engine"] == "supervision.ByteTrack"
    assert len(hub["zones"]) == 4
    assert hub["overflow_forecast"]["signal"]["signal_type"] == "HUB_OVERFLOW_RISK_FORECAST"

    summary = client.get("/api/visual-intelligence/summary").json()
    assert len(summary["chain"]) == 4
    assert "ETA" in summary["operational_effect"]

def test_cv_event_ingestion_and_replay(client):
    event = {
        "event_id": f"CVE-TEST-PACKAGE-DAMAGE-{uuid4().hex[:8]}",
        "event_type": "PACKAGE_DAMAGE_DETECTED",
        "module": "PACKAGE_QUALITY",
        "source": "TEST",
        "shipment_id": "SHP-1028",
        "confidence": 0.9,
        "severity": "HIGH",
        "payload": {"damage_type": "crushed"},
    }
    created = client.post("/api/cv/events", json=event).json()
    assert created["accepted"] is True
    assert created["duplicate"] is False
    duplicate = client.post("/api/cv/events", json=event).json()
    assert duplicate["duplicate"] is True
    state = client.get("/api/cv/state").json()
    assert state["event_count"] >= 1
    replay = client.post("/api/cv/demo-replay?scenario=HUB_CONGESTION").json()
    assert replay["events_sent"] == 1
    assert replay["results"][0]["accepted"] is True
