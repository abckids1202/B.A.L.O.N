from cv_worker.tracking.marker_logic import HubJourneySession, LoadingInspectionState


def det(x1, y1, x2, y2, confidence=0.9, raw_class="Large_Box"):
    return {
        "raw_class": raw_class,
        "normalized_class": "PACKAGE",
        "confidence": confidence,
        "bbox": [x1, y1, x2, y2],
        "centroid": [(x1 + x2) / 2, (y1 + y2) / 2],
    }


def marker(x, y=300, marker_id=1):
    return [{
        "track_id": f"MARKER-{marker_id}",
        "marker_id": marker_id,
        "center": [x, y],
        "bbox": [x - 10, y - 10, x + 10, y + 10],
        "source": "ARUCO",
    }]


def test_loading_snapshot_counts_once_and_freezes_until_recapture():
    state = LoadingInspectionState()
    result = state.capture([det(500, 200, 620, 360)], 1000, 600, 0.75)

    assert result["status"] == "COMPLETED"
    assert result["detected_package_count"] == 1
    assert result["loaded_packages"] == 1
    assert result["dispatch_state"] == "READY"

    frozen = state.summary(0.75)
    assert frozen["detected_package_count"] == 1


def test_loading_snapshot_over_capacity_and_dedupes_overlap():
    state = LoadingInspectionState()
    detections = [
        det(500, 100, 590, 210),
        det(505, 105, 595, 215, confidence=0.81),
        det(610, 100, 700, 210),
        det(720, 100, 810, 210),
        det(500, 260, 590, 370),
        det(610, 260, 700, 370),
        det(720, 260, 810, 370),
    ]
    result = state.capture(detections, 1000, 600, 0.75)

    assert result["detected_package_count"] == 6
    assert result["excess_count"] == 1
    assert result["capacity_status"] == "OVER_CAPACITY"
    assert result["dispatch_state"] == "BLOCKED"


def test_loading_reset_and_second_snapshot_replaces_result():
    state = LoadingInspectionState()
    state.capture([det(500, 200, 620, 360)], 1000, 600, 0.75)
    state.reset()
    ready = state.summary(0.75)
    assert ready["status"] == "READY"
    assert ready["detected_package_count"] == 0

    result = state.capture([det(500, 100, 590, 210), det(610, 100, 700, 210)], 1000, 600, 0.75)
    assert result["detected_package_count"] == 2
    assert result["snapshot_id"] == "LOAD-SNAPSHOT-0002"


def test_hub_start_requires_marker_in_zone_1():
    hub = HubJourneySession(baseline_seconds={"ZONE_1": 5, "ZONE_2": 8, "ZONE_3": 4})
    result = hub.start(marker(700), 900, 600, "ARUCO_IDENTITY", now=100)

    assert result["status"] == "READY"
    assert result["last_error"] == "PLACE PACKAGE IN ZONE 1"


def test_hub_projection_zone_1_and_zone_2_formula():
    hub = HubJourneySession(baseline_seconds={"ZONE_1": 5, "ZONE_2": 8, "ZONE_3": 4})
    hub.start(marker(100), 900, 600, "ARUCO_IDENTITY", now=100)
    zone_1 = hub.update(marker(100), 900, 600, "ARUCO_IDENTITY", now=107)
    assert zone_1["zone_1_seconds"] == 7.0
    assert zone_1["projected_total_seconds"] == 23.8
    assert zone_1["estimated_delay_seconds"] == 6.8
    assert zone_1["sla_risk_level"] == "HIGH"

    hub.update(marker(450), 900, 600, "ARUCO_IDENTITY", now=107)
    zone_2 = hub.update(marker(450), 900, 600, "ARUCO_IDENTITY", now=117)
    assert zone_2["zone_1_seconds"] == 7.0
    assert zone_2["zone_2_seconds"] == 10.0
    assert zone_2["projected_total_seconds"] == 22.2
    assert zone_2["estimated_delay_seconds"] == 5.2
    assert zone_2["transition_count"] == 1


def test_hub_stop_freezes_actual_total_and_reset_restarts():
    hub = HubJourneySession(baseline_seconds={"ZONE_1": 5, "ZONE_2": 8, "ZONE_3": 4})
    hub.start(marker(100), 900, 600, "ARUCO_IDENTITY", now=100)
    hub.update(marker(450), 900, 600, "ARUCO_IDENTITY", now=107)
    hub.update(marker(800), 900, 600, "ARUCO_IDENTITY", now=117)
    stopped = hub.stop(now=122)

    assert stopped["status"] == "COMPLETED"
    assert stopped["zone_1_seconds"] == 7.0
    assert stopped["zone_2_seconds"] == 10.0
    assert stopped["zone_3_seconds"] == 5.0
    assert stopped["actual_total_seconds"] == 22.0
    assert stopped["final_delay_seconds"] == 5.0

    hub.reset()
    restarted = hub.start(marker(100), 900, 600, "ARUCO_IDENTITY", now=200)
    assert restarted["status"] == "RUNNING"
    assert restarted["zone_1_seconds"] == 0.0
