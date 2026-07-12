from cv_worker.tracking.marker_logic import HubState, LoadingState


def observation(x, y=300, track_id="MARKER-1", source="ARUCO_IDENTITY"):
    marker_id = int(track_id.split("-")[-1]) if track_id.split("-")[-1].isdigit() else None
    return [{
        "track_id": track_id,
        "marker_id": marker_id,
        "center": [x, y],
        "bbox": [x - 10, y - 10, x + 10, y + 10],
        "source": source,
    }]


def test_loading_membership_counts_unique_markers_inside_roi():
    state = LoadingState()
    width, height = 1000, 600

    assert state.update(observation(200), width, height, "ARUCO_IDENTITY")["loaded_packages"] == 0
    entered = state.update(observation(500), width, height, "ARUCO_IDENTITY")
    assert entered["loaded_packages"] == 1
    assert entered["entry_events"] == 1

    stationary = state.update(observation(800), width, height, "ARUCO_IDENTITY")
    assert stationary["loaded_packages"] == 1
    assert stationary["entry_events"] == 1

    removed = state.update(observation(200), width, height, "ARUCO_IDENTITY")
    assert removed["loaded_packages"] == 0
    assert removed["exit_events"] == 1


def test_loading_sixth_package_blocks_and_removing_resolves():
    state = LoadingState()
    width, height = 1000, 600
    for index in range(1, 7):
        result = state.update(observation(500, track_id=f"MARKER-{index}"), width, height, "ARUCO_IDENTITY")
    assert result["loaded_packages"] == 6
    assert result["status"] == "BLOCKED"
    assert result["capacity_status"] == "OVER_CAPACITY"

    resolved = state.update(observation(200, track_id="MARKER-1"), width, height, "ARUCO_IDENTITY")
    assert resolved["loaded_packages"] == 5
    assert resolved["status"] == "READY"
    assert resolved["capacity_status"] == "WITHIN_LIMIT"


def test_loading_reset_accepts_new_marker_immediately():
    state = LoadingState()
    width, height = 1000, 600
    state.update(observation(500, track_id="MARKER-1"), width, height, "ARUCO_IDENTITY")
    state.reset()

    result = state.update(observation(500, track_id="MARKER-1"), width, height, "ARUCO_IDENTITY")
    assert result["loaded_packages"] == 1
    assert result["entry_events"] == 1
    assert result["loaded_marker_ids"] == ["MARKER-01"]


def test_hub_three_stage_journey_recomputes_zone_and_resets_current_timer():
    state = HubState(time_multiplier=1)
    width, height = 900, 600

    receiving = state.update(observation(100, 300), width, height, "ARUCO_IDENTITY")
    assert receiving["track_states"][0]["current_zone"] == "ZONE_1"
    assert receiving["track_states"][0]["current_stage"] == "RECEIVING"

    processing = state.update(observation(450, 300), width, height, "ARUCO_IDENTITY")
    assert processing["track_states"][0]["previous_zone"] == "ZONE_1"
    assert processing["track_states"][0]["current_zone"] == "ZONE_2"
    assert processing["track_states"][0]["current_stage"] == "PROCESSING"
    assert processing["track_states"][0]["transition_count"] == 1
    assert processing["track_states"][0]["current_zone_seconds"] == 0.0

    dispatch = state.update(observation(800, 300), width, height, "ARUCO_IDENTITY")
    assert dispatch["track_states"][0]["previous_zone"] == "ZONE_2"
    assert dispatch["track_states"][0]["current_zone"] == "ZONE_3"
    assert dispatch["track_states"][0]["current_stage"] == "DISPATCH"
    assert dispatch["track_states"][0]["transition_count"] == 2
    assert "total_journey_seconds" in dispatch["track_states"][0]
