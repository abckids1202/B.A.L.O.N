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
