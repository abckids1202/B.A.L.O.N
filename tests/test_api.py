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
