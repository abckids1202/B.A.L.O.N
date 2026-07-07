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
