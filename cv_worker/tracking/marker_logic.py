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
        {"zone_id": "INCOMING", "polygon": [[0.02, 0.08], [0.98, 0.08], [0.98, 0.36], [0.02, 0.36]], "capacity": 6},
        {"zone_id": "PROCESSING", "polygon": [[0.02, 0.36], [0.98, 0.36], [0.98, 0.68], [0.02, 0.68]], "capacity": 8},
        {"zone_id": "OUTGOING", "polygon": [[0.02, 0.68], [0.98, 0.68], [0.98, 0.96], [0.02, 0.96]], "capacity": 6},
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


def _vertical_side(point: list[float], line: list[list[float]], width: int, height: int) -> str:
    p1 = _scale_point(line[0], width, height)
    p2 = _scale_point(line[1], width, height)
    x_line = (p1[0] + p2[0]) / 2
    return "INSIDE" if point[0] >= x_line else "OUTSIDE"


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

    def reset(self) -> None:
        self.tracks.clear()
        self.loaded.clear()
        self.last_status = "READY"
        self.entry_crossings = 0
        self.exit_crossings = 0
        self.last_state_change = None

    def update(self, observations: list[dict], frame_width: int, frame_height: int, provider: str) -> dict:
        if frame_width <= 0 or frame_height <= 0:
            return self.summary(provider, [])
        now = time.time()
        active_ids = set()
        roi = _polygon_pixels(self.config["roi_polygon"], frame_width, frame_height)
        for obs in observations:
            track_id = str(obs["track_id"])
            center = [float(obs["center"][0]), float(obs["center"][1])]
            side = _vertical_side(center, self.config["entry_line"], frame_width, frame_height)
            inside_roi = _point_in_polygon(center, roi)
            track = self.tracks.setdefault(track_id, {
                "track_id": track_id,
                "first_seen_at": now,
                "previous_side": side,
                "current_side": side,
                "counted_as_loaded": track_id in self.loaded,
                "stable_frames": 0,
            })
            previous_side = track.get("current_side", side)
            track.update({
                "previous_centroid": track.get("current_centroid", center),
                "current_centroid": center,
                "previous_side": previous_side,
                "current_side": side,
                "inside_loading_roi": inside_roi,
                "last_seen_at": now,
                "stable_frames": max(int(track.get("stable_frames", 0)) + 1, int(obs.get("stable_frames", 0) or 0)),
                "source": obs.get("source", provider),
            })
            active_ids.add(track_id)
            stable = track["stable_frames"] >= 2 or provider == "ARUCO_IDENTITY"
            if stable and previous_side == "OUTSIDE" and side == "INSIDE" and inside_roi and track_id not in self.loaded:
                self.loaded.add(track_id)
                track["counted_as_loaded"] = True
                track["entry_crossed"] = True
                self.entry_crossings += 1
                self.last_state_change = f"{track_id} entered loading"
            exit_side = _vertical_side(center, self.config["exit_line"], frame_width, frame_height)
            previous_exit_side = track.get("previous_exit_side", exit_side)
            track["previous_exit_side"] = exit_side
            if previous_exit_side == "INSIDE" and exit_side == "OUTSIDE" and track_id in self.loaded:
                self.loaded.remove(track_id)
                track["counted_as_loaded"] = False
                track["exit_crossed"] = True
                self.exit_crossings += 1
                self.last_state_change = f"{track_id} removed from loading"
        for track_id, track in list(self.tracks.items()):
            if track_id not in active_ids and now - float(track.get("last_seen_at", now)) > 2.0:
                track["missing_since"] = track.get("missing_since") or now
        return self.summary(provider, observations)

    def summary(self, provider: str, observations: list[dict]) -> dict:
        count = len(self.loaded)
        status = "BLOCKED" if count > self.limit else "READY"
        changed = status != self.last_status
        self.last_status = status
        return {
            "provider": provider,
            "configured": True,
            "roi": self.config,
            "visible_packages": len(observations),
            "stable_tracks": len([t for t in self.tracks.values() if int(t.get("stable_frames", 0)) >= 2]),
            "loaded_packages": count,
            "visual_capacity": self.limit,
            "status": status,
            "dispatch_allowed": status == "READY",
            "entry_crossings": self.entry_crossings,
            "exit_crossings": self.exit_crossings,
            "loaded_track_ids": sorted(self.loaded),
            "track_states": list(self.tracks.values())[-8:],
            "changed": changed,
            "last_state_change": self.last_state_change,
        }


class HubState:
    def __init__(self, time_multiplier: float = 60.0, config: dict | None = None) -> None:
        self.time_multiplier = time_multiplier
        self.config = config or DEFAULT_HUB_ZONES
        self.tracks: dict[str, dict] = {}
        self.last_level = "LOW"
        self.last_pressure_zone = None

    def reset(self) -> None:
        self.tracks.clear()
        self.last_level = "LOW"
        self.last_pressure_zone = None

    def zone_for(self, center: list[float], width: int, height: int) -> str | None:
        for zone in self.config.get("zones", []):
            polygon = _polygon_pixels(zone["polygon"], width, height)
            if _point_in_polygon(center, polygon):
                return zone["zone_id"]
        return None

    def update(self, observations: list[dict], width: int, height: int, provider: str) -> dict:
        now = time.time()
        active_ids = set()
        transitions = []
        for obs in observations:
            track_id = str(obs["track_id"])
            center = [float(obs["center"][0]), float(obs["center"][1])]
            zone = self.zone_for(center, width, height) or "UNASSIGNED"
            current = self.tracks.get(track_id)
            if not current:
                self.tracks[track_id] = {
                    "track_id": track_id,
                    "current_zone": zone,
                    "previous_zone": None,
                    "zone_entered_at": now,
                    "first_seen_at": now,
                    "transition_count": 0,
                    "marker": obs,
                }
            elif current["current_zone"] != zone:
                current["previous_zone"] = current["current_zone"]
                current["current_zone"] = zone
                current["zone_entered_at"] = now
                current["transition_count"] = int(current.get("transition_count", 0)) + 1
                current["marker"] = obs
                transitions.append({"track_id": track_id, "from": current["previous_zone"], "to": zone})
            else:
                current["marker"] = obs
            self.tracks[track_id]["last_seen_at"] = now
            active_ids.add(track_id)
        by_zone: dict[str, int] = {}
        dwell_values = []
        track_summaries = []
        for track in self.tracks.values():
            zone = track["current_zone"]
            by_zone[zone] = by_zone.get(zone, 0) + 1
            dwell = (now - track["zone_entered_at"]) * self.time_multiplier / 60
            dwell_values.append(dwell)
            track_summaries.append({
                "track_id": track["track_id"],
                "previous_zone": track.get("previous_zone"),
                "current_zone": zone,
                "current_zone_dwell_min": round(dwell, 1),
                "transition_count": track.get("transition_count", 0),
            })
        queue = by_zone.get("PROCESSING", 0)
        avg_dwell = sum(dwell_values) / len(dwell_values) if dwell_values else 0
        occupancy = min(1.0, len(active_ids) / 12)
        flow_imbalance = max(0, queue - by_zone.get("OUTGOING", 0))
        score = min(100, round(occupancy * 25 + min(queue / 8, 1) * 20 + min(avg_dwell / 10, 1) * 25 + flow_imbalance * 3))
        level = "CRITICAL" if score >= 75 else "HIGH" if score >= 55 else "MODERATE" if score >= 30 else "LOW"
        main_zone = max(by_zone.items(), key=lambda item: item[1])[0] if by_zone else None
        changed = bool(transitions) or level != self.last_level or main_zone != self.last_pressure_zone
        self.last_level = level
        self.last_pressure_zone = main_zone
        return {
            "provider": provider,
            "configured": True,
            "zones": self.config.get("zones", []),
            "zone_counts": by_zone,
            "queue_length": queue,
            "average_dwell_min": round(avg_dwell, 1),
            "occupancy_ratio": round(occupancy, 2),
            "congestion_score": score,
            "congestion_level": level,
            "main_pressure_zone": main_zone,
            "transitions": transitions,
            "track_states": track_summaries[-8:],
            "changed": changed,
        }
