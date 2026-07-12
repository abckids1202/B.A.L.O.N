from cv_worker.tracking.marker_logic import HubState, LoadingState


def observation(x, y=300, track_id="MARKER-1", source="ARUCO_IDENTITY"):
    return [{
        "track_id": track_id,
        "center": [x, y],
        "bbox": [x - 10, y - 10, x + 10, y + 10],
        "source": source,
    }]


def test_loading_line_crossing_increments_once_and_decrements():
    state = LoadingState()
    width, height = 1000, 600

    assert state.update(observation(200), width, height, "ARUCO_IDENTITY")["loaded_packages"] == 0
    entered = state.update(observation(500), width, height, "ARUCO_IDENTITY")
    assert entered["loaded_packages"] == 1
    assert entered["entry_crossings"] == 1

    stationary = state.update(observation(800), width, height, "ARUCO_IDENTITY")
    assert stationary["loaded_packages"] == 1
    assert stationary["entry_crossings"] == 1

    removed = state.update(observation(200), width, height, "ARUCO_IDENTITY")
    assert removed["loaded_packages"] == 0
    assert removed["exit_crossings"] == 1


def test_loading_sixth_package_blocks_and_removing_resolves():
    state = LoadingState()
    width, height = 1000, 600
    for index in range(6):
        track_id = f"MARKER-{index}"
        state.update(observation(200, track_id=track_id), width, height, "ARUCO_IDENTITY")
        result = state.update(observation(500, track_id=track_id), width, height, "ARUCO_IDENTITY")
    assert result["loaded_packages"] == 6
    assert result["status"] == "BLOCKED"

    resolved = state.update(observation(200, track_id="MARKER-0"), width, height, "ARUCO_IDENTITY")
    assert resolved["loaded_packages"] == 5
    assert resolved["status"] == "READY"


def test_hub_zone_recomputes_and_resets_dwell_on_transition():
    state = HubState(time_multiplier=60)
    width, height = 1000, 600

    incoming = state.update(observation(500, 100), width, height, "ARUCO_IDENTITY")
    assert incoming["track_states"][0]["current_zone"] == "INCOMING"

    sorting = state.update(observation(300, 320), width, height, "ARUCO_IDENTITY")
    assert sorting["track_states"][0]["previous_zone"] == "INCOMING"
    assert sorting["track_states"][0]["current_zone"] == "PROCESSING"
    assert sorting["track_states"][0]["transition_count"] == 1
    assert sorting["track_states"][0]["current_zone_dwell_min"] == 0.0

    loading = state.update(observation(500, 500), width, height, "ARUCO_IDENTITY")
    assert loading["track_states"][0]["previous_zone"] == "PROCESSING"
    assert loading["track_states"][0]["current_zone"] == "OUTGOING"
    assert loading["track_states"][0]["transition_count"] == 2
