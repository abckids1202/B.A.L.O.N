import cv2

from cv_worker.runtime import CVRuntime
from cv_worker.tracking.marker_logic import LoadingInspectionState


def test_loading_snapshot_ignores_marker_tracking_and_counts_yolo_boxes():
    state = LoadingInspectionState()
    result = state.capture([{
        "raw_class": "Large_Box",
        "normalized_class": "PACKAGE",
        "confidence": 0.93,
        "bbox": [500, 100, 650, 260],
        "centroid": [575, 180],
    }], 1000, 600, 0.75)

    assert result["detected_package_count"] == 1
    assert result["inspection_type"] == "SNAPSHOT"
    assert result["dispatch_state"] == "READY"


def test_loading_snapshot_reset_clears_state():
    state = LoadingInspectionState()
    state.capture([{
        "raw_class": "Large_Box",
        "normalized_class": "PACKAGE",
        "confidence": 0.93,
        "bbox": [500, 100, 650, 260],
        "centroid": [575, 180],
    }], 1000, 600, 0.75)
    state.reset()
    reset = state.summary(0.75)
    assert reset["status"] == "READY"
    assert reset["detected_package_count"] == 0
    assert reset["valid_detections"] == []


def test_dispatch_uses_seeded_assignment_for_non_load_qr():
    runtime = CVRuntime()
    runtime.backend_enabled = False
    runtime.mode = "DISPATCH_VALIDATION"
    runtime.set_loading_context("WRONG")
    image = cv2.imread("data/demo_qr/SHP-DMG-001.png")

    runtime.analyze_frame(image)

    assert runtime.last_event["event_type"] == "PACKAGE_LOADING_MISMATCH"
    assert runtime.last_event["payload"]["validation_result"] == "WRONG_VEHICLE"
    assert runtime.last_event["payload"]["dispatch_state"] == "DISPATCH_BLOCKED"
    assert runtime.last_event["payload"]["expected_vehicle_id"] == "VAN-021"
    assert runtime.last_event["payload"]["observed_vehicle_id"] == "VAN-044"


def test_s_does_not_start_hub_journey():
    runtime = CVRuntime()
    runtime.backend_enabled = False
    runtime.mode = "HUB_VISION"

    result = runtime.start_active_module(None)

    assert result["accepted"] is False
    assert "Use H" in result["error"]
    assert runtime.hub_state.status == "READY"


def test_yolo_candidate_starts_hub_when_marker_absent():
    runtime = CVRuntime()
    runtime.backend_enabled = False
    runtime.mode = "HUB_VISION"
    width, height = 900, 600
    detection = {
        "raw_class": "Large_Box",
        "normalized_class": "PACKAGE",
        "confidence": 0.93,
        "bbox": [80, 100, 230, 260],
        "centroid": [155, 180],
    }
    for _ in range(3):
        runtime._record_hub_yolo_history([detection])

    candidate = runtime._resolve_hub_candidate([], [detection], width, height, require_zone_1=True)
    result = runtime.hub_state.start(candidate, width, height, "YOLO_SINGLE_PACKAGE", now=100)

    assert candidate["source"] == "YOLO_SINGLE_PACKAGE"
    assert candidate["zone"] == "ZONE_1"
    assert candidate["stable_frames"] >= 3
    assert result["status"] == "RUNNING"
    assert result["provider"] == "YOLO_SINGLE_PACKAGE"
