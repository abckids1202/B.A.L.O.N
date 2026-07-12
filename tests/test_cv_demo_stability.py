import cv2

from cv_worker.runtime import CVRuntime
from cv_worker.tracking.marker_logic import LoadingState


def marker(track_id, x, y=300):
    return [{
        "track_id": track_id,
        "marker_id": int(track_id.split("-")[-1]),
        "center": [x, y],
        "bbox": [x - 10, y - 10, x + 10, y + 10],
        "source": "ARUCO",
    }]


def test_default_loading_provider_ignores_unmarked_yolo_centroid():
    runtime = CVRuntime()
    runtime.mode = "LOADING_COMPLIANCE"
    provider, observations = runtime._tracking_observations([], [{
        "raw_class": "Large_Box",
        "normalized_class": "PACKAGE",
        "confidence": 0.93,
        "bbox": [100, 100, 300, 300],
        "centroid": [500, 300],
    }])

    assert provider == "ARUCO_WAITING_FOR_MARKER"
    assert observations == []
    loading = runtime.loading_state.update(observations, 1000, 600, provider)
    assert loading["loaded_packages"] == 0
    assert loading["entry_crossings"] == 0


def test_six_unique_markers_block_and_reset_clears_state():
    state = LoadingState()
    width, height = 1000, 600
    result = None
    for index in range(1, 7):
        track_id = f"MARKER-{index}"
        state.update(marker(track_id, 200), width, height, "ARUCO_IDENTITY")
        result = state.update(marker(track_id, 500), width, height, "ARUCO_IDENTITY")

    assert result["loaded_packages"] == 6
    assert result["status"] == "BLOCKED"
    assert result["loaded_track_ids"] == [f"MARKER-{i:02d}" for i in range(1, 7)]

    state.reset()
    reset = state.summary("ARUCO_IDENTITY", [])
    assert reset["loaded_packages"] == 0
    assert reset["entry_crossings"] == 0
    assert reset["exit_crossings"] == 0
    assert reset["status"] == "READY"


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
