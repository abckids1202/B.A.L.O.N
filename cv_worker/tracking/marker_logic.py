from __future__ import annotations

import time


DEFAULT_LOADING_CONFIG = {
    "configured_package_limit": 5,
    "roi_polygon": [[0.45, 0.14], [0.96, 0.14], [0.96, 0.92], [0.45, 0.92]],
    "entry_line": [[0.45, 0.14], [0.45, 0.92]],
    "exit_line": [[0.25, 0.14], [0.25, 0.92]],
}

DEFAULT_HUB_ZONES = {
    "zones": [
        {"zone_id": "ZONE_1", "name": "RECEIVING", "x_min": 0.0, "x_max": 0.3333, "capacity": 6},
        {"zone_id": "ZONE_2", "name": "PROCESSING", "x_min": 0.3333, "x_max": 0.6666, "capacity": 8},
        {"zone_id": "ZONE_3", "name": "DISPATCH", "x_min": 0.6666, "x_max": 1.0, "capacity": 6},
    ]
}


def _scale_point(point: list[float], width: int, height: int) -> list[float]:
    x, y = point
    if 0 <= x <= 1 and 0 <= y <= 1:
        return [x * width, y * height]
    return [x, y]


def _polygon_pixels(poly: list[list[float]], width: int, height: int) -> list[list[float]]:
    return [_scale_point(point, width, height) for point in poly]


def _point_in_polygon(point: list[float], polygon: list[list[float]]) -> bool:
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersects = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi)
        if intersects:
            inside = not inside
        j = i
    return inside


def _display_marker(marker_key: str) -> str:
    try:
        return f"MARKER-{int(marker_key):02d}"
    except (TypeError, ValueError):
        return str(marker_key)


def _marker_key(obs: dict) -> str:
    marker_id = obs.get("marker_id")
    if marker_id is not None:
        return str(marker_id)
    track_id = str(obs.get("track_id", "UNKNOWN"))
    if "-" in track_id:
        suffix = track_id.rsplit("-", 1)[-1]
        if suffix.isdigit():
            return str(int(suffix))
    return track_id


class LoadingState:
    def __init__(self, limit: int = 5, config: dict | None = None) -> None:
        self.config = {**DEFAULT_LOADING_CONFIG, **(config or {})}
        self.limit = int(self.config.get("configured_package_limit") or limit)
        self.tracks: dict[str, dict] = {}
        self.loaded: set[str] = set()
        self.last_status = "READY"
        self.entry_crossings = 0
        self.exit_crossings = 0
        self.last_state_change = None
        self.last_change_kind = None

    def reset(self) -> None:
        self.tracks.clear()
        self.loaded.clear()
        self.last_status = "READY"
        self.entry_crossings = 0
        self.exit_crossings = 0
        self.last_state_change = None
        self.last_change_kind = None

    def update(self, observations: list[dict], frame_width: int, frame_height: int, provider: str) -> dict:
        if frame_width <= 0 or frame_height <= 0:
            return self.summary(provider, [])

        now = time.time()
        active_keys = set()
        roi = _polygon_pixels(self.config["roi_polygon"], frame_width, frame_height)

        for obs in observations:
            marker_key = _marker_key(obs)
            display_id = _display_marker(marker_key)
            center = [float(obs["center"][0]), float(obs["center"][1])]
            inside_roi = _point_in_polygon(center, roi)
            track = self.tracks.setdefault(marker_key, {
                "marker_id": marker_key,
                "track_id": display_id,
                "first_seen_at": now,
                "current_inside_roi": False,
                "counted_as_loaded": False,
                "stable_frames": 0,
            })
            previous_inside = bool(track.get("current_inside_roi", False))
            track.update({
                "track_id": display_id,
                "previous_centroid": track.get("current_centroid", center),
                "current_centroid": center,
                "previous_inside_roi": previous_inside,
                "current_inside_roi": inside_roi,
                "inside_loading_roi": inside_roi,
                "last_seen_at": now,
                "stable_frames": max(int(track.get("stable_frames", 0)) + 1, int(obs.get("stable_frames", 0) or 0)),
                "source": obs.get("source", provider),
                "shipment_id": obs.get("shipment_id"),
                "package_id": obs.get("package_id"),
            })
            active_keys.add(marker_key)

            if inside_roi and not previous_inside and marker_key not in self.loaded:
                self.loaded.add(marker_key)
                track["counted_as_loaded"] = True
                self.entry_crossings += 1
                self.last_change_kind = "ENTERED"
                self.last_state_change = f"{display_id} entered loading ROI"
            elif not inside_roi and previous_inside and marker_key in self.loaded:
                self.loaded.remove(marker_key)
                track["counted_as_loaded"] = False
                self.exit_crossings += 1
                self.last_change_kind = "REMOVED"
                self.last_state_change = f"{display_id} left loading ROI"

        for marker_key, track in list(self.tracks.items()):
            if marker_key not in active_keys:
                track["missing_since"] = track.get("missing_since") or now

        return self.summary(provider, observations)

    def summary(self, provider: str, observations: list[dict]) -> dict:
        count = len(self.loaded)
        status = "BLOCKED" if count > self.limit else "READY"
        changed = status != self.last_status or self.last_change_kind is not None
        self.last_status = status
        loaded_ids = sorted((_display_marker(item) for item in self.loaded), key=str)
        visible_ids = sorted((_display_marker(_marker_key(obs)) for obs in observations), key=str)
        over_capacity = max(0, count - self.limit)
        return {
            "provider": provider,
            "configured": True,
            "roi": self.config,
            "visible_packages": len(observations),
            "visible_marker_ids": visible_ids,
            "active_marker_count": len(visible_ids),
            "stable_tracks": len([t for t in self.tracks.values() if int(t.get("stable_frames", 0)) >= 1]),
            "loaded_packages": count,
            "loaded_marker_ids": loaded_ids,
            "loaded_track_ids": loaded_ids,
            "visual_capacity": self.limit,
            "configured_package_limit": self.limit,
            "excess_count": over_capacity,
            "capacity_status": "OVER_CAPACITY" if over_capacity else "WITHIN_LIMIT",
            "status": status,
            "dispatch_state": "BLOCKED" if status == "BLOCKED" else "READY",
            "dispatch_allowed": status == "READY",
            "recommendation": "Remove one marked package from the vehicle ROI" if status == "BLOCKED" else "Dispatch can proceed",
            "entry_crossings": self.entry_crossings,
            "exit_crossings": self.exit_crossings,
            "entry_events": self.entry_crossings,
            "exit_events": self.exit_crossings,
            "track_states": list(self.tracks.values())[-8:],
            "changed": changed,
            "last_change_kind": self.last_change_kind,
            "last_state_change": self.last_state_change,
        }


class HubState:
    def __init__(self, time_multiplier: float = 1.0, config: dict | None = None) -> None:
        self.time_multiplier = time_multiplier
        self.config = config or DEFAULT_HUB_ZONES
        self.tracks: dict[str, dict] = {}
        self.last_signature = None

    def reset(self) -> None:
        self.tracks.clear()
        self.last_signature = None

    def _zone_name(self, zone_id: str | None) -> str:
        for zone in self.config.get("zones", []):
            if zone.get("zone_id") == zone_id:
                return zone.get("name") or zone_id or "UNASSIGNED"
        return zone_id or "UNASSIGNED"

    def zone_for(self, center: list[float], width: int, height: int) -> str | None:
        x = float(center[0])
        x_norm = x / max(width, 1)
        for zone in self.config.get("zones", []):
            if "x_min" in zone and "x_max" in zone:
                if float(zone["x_min"]) <= x_norm < float(zone["x_max"]) or (x_norm <= 1 and float(zone["x_max"]) >= 1 and x_norm <= float(zone["x_max"])):
                    return zone["zone_id"]
            elif zone.get("polygon"):
                polygon = _polygon_pixels(zone["polygon"], width, height)
                if _point_in_polygon(center, polygon):
                    return zone["zone_id"]
        return None

    def _risk(self, seconds: float, first_threshold: float, second_threshold: float) -> str:
        if seconds >= second_threshold:
            return "HIGH"
        if seconds >= first_threshold:
            return "MODERATE"
        return "LOW"

    def update(self, observations: list[dict], width: int, height: int, provider: str) -> dict:
        now = time.time()
        active_keys = set()
        transitions = []
        zone_ids = [zone["zone_id"] for zone in self.config.get("zones", [])]

        for obs in observations:
            marker_key = _marker_key(obs)
            display_id = _display_marker(marker_key)
            center = [float(obs["center"][0]), float(obs["center"][1])]
            zone = self.zone_for(center, width, height) or "UNASSIGNED"
            current = self.tracks.get(marker_key)
            if not current:
                self.tracks[marker_key] = {
                    "marker_id": marker_key,
                    "track_id": display_id,
                    "current_zone": zone,
                    "previous_zone": None,
                    "zone_entered_at": now,
                    "first_seen_at": now,
                    "journey_started_at": now,
                    "transition_count": 0,
                    "zone_durations": {zone_id: 0.0 for zone_id in zone_ids},
                    "marker": obs,
                    "completed": False,
                }
            elif current["current_zone"] != zone:
                old_zone = current["current_zone"]
                if old_zone in current["zone_durations"]:
                    current["zone_durations"][old_zone] += max(0.0, now - float(current.get("zone_entered_at", now))) * self.time_multiplier
                current["previous_zone"] = old_zone
                current["current_zone"] = zone
                current["zone_entered_at"] = now
                current["transition_count"] = int(current.get("transition_count", 0)) + 1
                current["marker"] = obs
                current["completed"] = zone == "ZONE_3" and current["transition_count"] >= 2
                transitions.append({"track_id": display_id, "from": old_zone, "to": zone})
            else:
                current["marker"] = obs
            self.tracks[marker_key]["last_seen_at"] = now
            active_keys.add(marker_key)

        by_zone: dict[str, int] = {}
        track_summaries = []
        for track in self.tracks.values():
            zone = track["current_zone"]
            by_zone[zone] = by_zone.get(zone, 0) + 1
            durations = dict(track.get("zone_durations") or {})
            if zone in durations:
                durations[zone] += max(0.0, now - float(track.get("zone_entered_at", now))) * self.time_multiplier
            zone_1 = round(float(durations.get("ZONE_1", 0.0)), 1)
            zone_2 = round(float(durations.get("ZONE_2", 0.0)), 1)
            zone_3 = round(float(durations.get("ZONE_3", 0.0)), 1)
            current_seconds = round(max(0.0, now - float(track.get("zone_entered_at", now))) * self.time_multiplier, 1)
            cumulative_delay = zone_1 + zone_2
            total = zone_1 + zone_2 + zone_3
            track_summaries.append({
                "track_id": track["track_id"],
                "marker_id": _display_marker(track.get("marker_id")),
                "previous_zone": track.get("previous_zone"),
                "previous_zone_name": self._zone_name(track.get("previous_zone")),
                "current_zone": zone,
                "current_zone_name": self._zone_name(zone),
                "current_stage": self._zone_name(zone),
                "current_zone_seconds": current_seconds,
                "zone_1_seconds": zone_1,
                "zone_2_seconds": zone_2,
                "zone_3_seconds": zone_3,
                "cumulative_delay_seconds": round(cumulative_delay, 1),
                "total_journey_seconds": round(total, 1),
                "transition_count": track.get("transition_count", 0),
                "journey_status": "COMPLETE" if track.get("completed") else "IN_PROGRESS",
                "zone_1_risk": self._risk(zone_1, 5, 10),
                "cumulative_risk": self._risk(cumulative_delay, 12, 20),
            })

        latest_track = track_summaries[-1] if track_summaries else {}
        signature = (
            tuple(sorted(by_zone.items())),
            latest_track.get("track_id"),
            latest_track.get("current_zone"),
            latest_track.get("transition_count"),
            latest_track.get("cumulative_risk"),
        )
        changed = bool(transitions) or signature != self.last_signature
        self.last_signature = signature
        total_tracks = sum(by_zone.values())
        return {
            "provider": provider,
            "configured": True,
            "zones": self.config.get("zones", []),
            "zone_counts": by_zone,
            "active_marker_count": total_tracks,
            "queue_length": by_zone.get("ZONE_2", 0),
            "average_dwell_min": round(float(latest_track.get("current_zone_seconds", 0)) / 60, 1) if latest_track else 0,
            "occupancy_ratio": round(min(1.0, total_tracks / 12), 2),
            "congestion_score": 0,
            "congestion_level": latest_track.get("cumulative_risk", "LOW") if latest_track else "LOW",
            "journey_status": latest_track.get("journey_status", "WAITING"),
            "current_stage": latest_track.get("current_stage", "WAITING_FOR_MARKER"),
            "main_pressure_zone": latest_track.get("current_zone"),
            "transitions": transitions,
            "track_states": track_summaries[-8:],
            "changed": changed,
        }
