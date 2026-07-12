from cv_worker.tracking.marker_logic import HubJourneySession, LoadingInspectionState, make_marker_candidate, make_yolo_candidate


def det(x1, y1, x2, y2, confidence=0.9, raw_class="Large_Box"):
    return {
        "raw_class": raw_class,
        "normalized_class": "PACKAGE",
        "confidence": confidence,
        "bbox": [x1, y1, x2, y2],
        "centroid": [(x1 + x2) / 2, (y1 + y2) / 2],
    }


def marker_candidate(x, y=300, marker_id=1, zone="ZONE_1"):
    return make_marker_candidate({
        "track_id": f"MARKER-{marker_id}",
        "marker_id": marker_id,
        "center": [x, y],
        "bbox": [x - 10, y - 10, x + 10, y + 10],
        "source": "ARUCO",
    }, zone=zone)


def yolo_candidate(x1, y1, x2, y2, zone="ZONE_1", confidence=0.9, stable=3):
    return make_yolo_candidate(det(x1, y1, x2, y2, confidence=confidence), zone=zone, stable_frames=stable)


def test_loading_snapshot_counts_once_and_freezes_until_recapture():
    state = LoadingInspectionState()
    result = state.capture([det(500, 200, 620, 360)], 1000, 600, 0.75)

    assert result["status"] == "COMPLETED"
    assert result["detected_package_count"] == 1
    assert result["loaded_packages"] == 1
    assert result["dispatch_state"] == "READY"
    assert state.summary(0.75)["detected_package_count"] == 1


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
    assert state.summary(0.75)["status"] == "READY"

    result = state.capture([det(500, 100, 590, 210), det(610, 100, 700, 210)], 1000, 600, 0.75)
    assert result["detected_package_count"] == 2
    assert result["snapshot_id"] == "LOAD-SNAPSHOT-0002"


def test_hub_start_requires_candidate_in_zone_1():
    hub = HubJourneySession()
    result = hub.start(yolo_candidate(650, 100, 760, 260, zone="ZONE_3"), 900, 600, "YOLO_SINGLE_PACKAGE", now=100)

    assert result["status"] == "READY"
    assert result["last_error"] == "PLACE PACKAGE IN ZONE 1"


def test_hub_yolo_candidate_can_start_without_marker():
    hub = HubJourneySession()
    started = hub.start(yolo_candidate(80, 100, 230, 260, zone="ZONE_1"), 900, 600, "YOLO_SINGLE_PACKAGE", now=100)

    assert started["status"] == "RUNNING"
    assert started["provider"] == "YOLO_SINGLE_PACKAGE"
    assert started["identity"] == "YOLO-PACKAGE-01"


def test_hub_projection_zone_1_and_zone_2_weighted_formula():
    hub = HubJourneySession(
        demo_baseline_seconds={"ZONE_1": 10, "ZONE_2": 10, "ZONE_3": 4},
        real_baseline_hours={"ZONE_1": 72.48, "ZONE_2": 72.0, "ZONE_3": 3.5},
    )
    hub.start(yolo_candidate(80, 100, 230, 260, zone="ZONE_1"), 900, 600, "YOLO_SINGLE_PACKAGE", now=100)
    zone_1 = hub.update(yolo_candidate(80, 100, 230, 260, zone="ZONE_1"), 900, 600, "YOLO_SINGLE_PACKAGE", now=113)
    assert zone_1["zone_1_seconds"] == 13.0
    assert zone_1["stage_factor_zone_1"] == 1.3
    assert zone_1["projected_real_dwell_hours"] == 192.4
    assert zone_1["estimated_delay_hours"] == 44.4
    assert zone_1["risk_level"] == "HIGH"

    hub.update(yolo_candidate(370, 100, 520, 260, zone="ZONE_2"), 900, 600, "YOLO_SINGLE_PACKAGE", now=113)
    zone_2 = hub.update(yolo_candidate(370, 100, 520, 260, zone="ZONE_2"), 900, 600, "YOLO_SINGLE_PACKAGE", now=121)
    assert zone_2["zone_1_seconds"] == 13.0
    assert zone_2["zone_2_seconds"] == 8.0
    assert zone_2["projected_real_dwell_hours"] == 155.5
    assert zone_2["estimated_delay_hours"] == 7.5
    assert zone_2["risk_level"] == "LOW"


def test_hub_stop_freezes_projected_real_dwell_and_reset_restarts():
    hub = HubJourneySession(
        demo_baseline_seconds={"ZONE_1": 10, "ZONE_2": 10, "ZONE_3": 4},
        real_baseline_hours={"ZONE_1": 72.48, "ZONE_2": 72.0, "ZONE_3": 3.5},
    )
    hub.start(yolo_candidate(80, 100, 230, 260, zone="ZONE_1"), 900, 600, "YOLO_SINGLE_PACKAGE", now=100)
    hub.update(yolo_candidate(370, 100, 520, 260, zone="ZONE_2"), 900, 600, "YOLO_SINGLE_PACKAGE", now=113)
    hub.update(yolo_candidate(700, 100, 850, 260, zone="ZONE_3"), 900, 600, "YOLO_SINGLE_PACKAGE", now=124)
    stopped = hub.stop(now=127)

    assert stopped["status"] == "COMPLETED"
    assert stopped["demo_total_seconds"] == 27.0
    assert stopped["zone_1_demo_seconds"] == 13.0
    assert stopped["zone_2_demo_seconds"] == 11.0
    assert stopped["zone_3_demo_seconds"] == 3.0
    assert stopped["projected_real_dwell_hours"] == 176.0
    assert stopped["estimated_delay_hours"] == 28.1
    assert stopped["risk_level"] == "MODERATE"

    hub.reset()
    restarted = hub.start(yolo_candidate(80, 100, 230, 260, zone="ZONE_1"), 900, 600, "YOLO_SINGLE_PACKAGE", now=200)
    assert restarted["status"] == "RUNNING"
    assert restarted["zone_1_seconds"] == 0.0


def test_hub_missing_target_enters_lost_state_after_grace():
    hub = HubJourneySession()
    hub.start(yolo_candidate(80, 100, 230, 260, zone="ZONE_1"), 900, 600, "YOLO_SINGLE_PACKAGE", now=100)
    first_missing = hub.update(None, 900, 600, "YOLO_SINGLE_PACKAGE", now=101)
    paused = hub.update(None, 900, 600, "YOLO_SINGLE_PACKAGE", now=101.6)
    lost = hub.update(None, 900, 600, "YOLO_SINGLE_PACKAGE", now=102.6)

    assert first_missing["target_status"] == "LOCKED"
    assert paused["target_status"] == "TARGET TEMPORARILY LOST"
    assert lost["target_status"] == "TARGET LOST - STOP OR RESET"

