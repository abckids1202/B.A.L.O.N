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
