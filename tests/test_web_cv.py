import numpy as np
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import web_cv
from scripts.generate_demo_data import main as seed
from scripts import seed_cv_demo_data


class FakeDamage:
    def predict(self, image):
        return {"label": "DAMAGED", "confidence": 0.87, "processing_time_ms": 3.2}


def fake_decode(*args, **kwargs):
    return np.zeros((100, 100, 3), dtype=np.uint8), {"filename": "test.jpg", "content_type": "image/jpeg", "image_width": 100, "image_height": 100, "sha1": "test"}


def fake_detect(frame):
    return {
        "processing_time_ms": 4.2,
        "detections": [
            {"raw_class": "Regular_Box", "normalized_class": "PACKAGE", "confidence": 0.91, "bbox": [10, 20, 30, 60], "centroid": [20, 40]},
            {"raw_class": "Large_Box", "normalized_class": "PACKAGE", "confidence": 0.88, "bbox": [50, 10, 58, 20], "centroid": [54, 15]},
            {"raw_class": "Large_Box", "normalized_class": "PACKAGE", "confidence": 0.87, "bbox": [60, 22, 68, 32], "centroid": [64, 27]},
            {"raw_class": "Large_Box", "normalized_class": "PACKAGE", "confidence": 0.86, "bbox": [70, 34, 78, 44], "centroid": [74, 39]},
            {"raw_class": "Large_Box", "normalized_class": "PACKAGE", "confidence": 0.85, "bbox": [80, 46, 88, 56], "centroid": [84, 51]},
            {"raw_class": "Large_Box", "normalized_class": "PACKAGE", "confidence": 0.84, "bbox": [88, 58, 96, 68], "centroid": [92, 63]},
        ],
    }


def client():
    seed()
    seed_cv_demo_data.main()
    return TestClient(app)


def patch_cv(monkeypatch):
    monkeypatch.setattr(web_cv, "_decode_image", fake_decode)
    monkeypatch.setattr(web_cv, "_detect", fake_detect)
    monkeypatch.setattr(web_cv, "damage_model", lambda: FakeDamage())


def test_web_cv_health_and_session():
    api = client()
    health = api.get("/api/web-cv/health").json()
    assert health["web_cv_enabled"] is True
    created = api.post("/api/web-cv/sessions", json={"module": "PACKAGE_QUALITY", "processing_mode": "LIVE_CAMERA"}).json()
    assert created["session_id"].startswith("WCV-")
    assert created["status"] == "READY"


def test_web_cv_package_quality_endpoint(monkeypatch):
    patch_cv(monkeypatch)
    api = client()
    session = api.post("/api/web-cv/sessions", json={"module": "PACKAGE_QUALITY"}).json()
    response = api.post("/api/web-cv/package-quality/analyze", data={"session_id": session["session_id"]}, files={"file": ("box.jpg", b"fake", "image/jpeg")})
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["status"] == "INSPECTION_REQUIRED"
    assert payload["event"]["observation"]["event_type"] == "PACKAGE_DAMAGE_DETECTED"


def test_web_cv_dispatch_wrong_and_correct_context(monkeypatch):
    patch_cv(monkeypatch)
    monkeypatch.setattr(web_cv, "_scan_qr", lambda frame: {"payload": {"shipment_id": "SHP-LOAD-001", "package_id": "PKG-LOAD-001"}, "raw": "SHP-LOAD-001", "points": None})
    api = client()
    session = api.post("/api/web-cv/sessions", json={"module": "DISPATCH_VALIDATION"}).json()
    wrong = api.post("/api/web-cv/dispatch/scan", data={"session_id": session["session_id"], "context_id": "CTX-JKT-BAY-02"}, files={"file": ("qr.jpg", b"fake", "image/jpeg")}).json()
    assert wrong["decision"]["status"] == "WRONG_VEHICLE"
    correct = api.post("/api/web-cv/dispatch/scan", data={"session_id": session["session_id"], "context_id": "CTX-JKT-BAY-01"}, files={"file": ("qr.jpg", b"fake", "image/jpeg")}).json()
    assert correct["decision"]["status"] == "VALID"


def test_web_cv_loading_snapshot_counts_once(monkeypatch):
    patch_cv(monkeypatch)
    api = client()
    session = api.post("/api/web-cv/sessions", json={"module": "LOADING_COMPLIANCE"}).json()
    response = api.post("/api/web-cv/loading/snapshot", data={"session_id": session["session_id"], "vehicle_id": "VAN-021"}, files={"file": ("load.jpg", b"fake", "image/jpeg")}).json()
    assert response["analysis"]["detected_package_count"] == 5
    assert response["decision"]["dispatch"] == "READY"


def test_web_cv_hub_journey_start_and_stop(monkeypatch):
    patch_cv(monkeypatch)
    api = client()
    session = api.post("/api/web-cv/sessions", json={"module": "HUB_JOURNEY"}).json()
    started = api.post("/api/web-cv/hub/start", data={"session_id": session["session_id"]}, files={"file": ("hub.jpg", b"fake", "image/jpeg")}).json()
    assert started["analysis"]["status"] == "RUNNING"
    stopped = api.post("/api/web-cv/hub/stop", json={"session_id": session["session_id"]}).json()
    assert stopped["decision"]["status"] == "JOURNEY_COMPLETED"
