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


def _display_marker(marker_key: str | int | None) -> str:
    try:
        return f"MARKER-{int(marker_key):02d}"
    except (TypeError, ValueError):
        return str(marker_key or "UNKNOWN")


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


def _bbox_iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = [float(v) for v in a]
    bx1, by1, bx2, by2 = [float(v) for v in b]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union else 0.0


class LoadingInspectionState:
    def __init__(self, limit: int = 5, config: dict | None = None) -> None:
        self.config = {**DEFAULT_LOADING_CONFIG, **(config or {})}
        self.limit = int(self.config.get("configured_package_limit") or limit)
        self.snapshot_index = 0
        self.reset()

    def reset(self) -> None:
        self.status = "READY"
        self.started_at = None
        self.completed_at = None
        self.snapshot_id = None
        self.valid_detections: list[dict] = []
        self.raw_detection_count = 0
        self.count = 0
        self.excess_count = 0
        self.capacity_status = "WITHIN_LIMIT"
        self.dispatch_state = "READY"
        self.recommendation = "Arrange packages inside ROI and press S"
        self.snapshot_path = None
        self.last_error = None

    def _filter_valid(self, detections: list[dict], width: int, height: int) -> list[dict]:
        roi = _polygon_pixels(self.config["roi_polygon"], width, height)
        valid = []
        for item in detections:
            raw = item.get("raw_class")
            normalized = item.get("normalized_class")
            if raw not in {"Regular_Box", "Large_Box"} and normalized != "PACKAGE":
                continue
            centroid = item.get("centroid") or [
                (float(item["bbox"][0]) + float(item["bbox"][2])) / 2,
                (float(item["bbox"][1]) + float(item["bbox"][3])) / 2,
            ]
            if not _point_in_polygon([float(centroid[0]), float(centroid[1])], roi):
                continue
            valid.append({**item, "normalized_class": "PACKAGE", "centroid": [round(float(centroid[0]), 1), round(float(centroid[1]), 1)]})
        return valid

    def _dedupe(self, detections: list[dict], iou_threshold: float = 0.45) -> list[dict]:
        kept: list[dict] = []
        for item in sorted(detections, key=lambda row: float(row.get("confidence", 0)), reverse=True):
            if all(_bbox_iou(item["bbox"], chosen["bbox"]) < iou_threshold for chosen in kept):
                kept.append(item)
        return kept

    def capture(self, detections: list[dict], width: int, height: int, confidence_threshold: float, snapshot_path: str | None = None) -> dict:
        self.status = "ANALYZING"
        self.started_at = time.time()
        self.snapshot_index += 1
        self.snapshot_id = f"LOAD-SNAPSHOT-{self.snapshot_index:04d}"
        self.raw_detection_count = len(detections)
        valid = self._dedupe(self._filter_valid(detections, width, height))
        self.valid_detections = valid
        self.count = len(valid)
        self.excess_count = max(0, self.count - self.limit)
        self.capacity_status = "OVER_CAPACITY" if self.excess_count else "WITHIN_LIMIT"
        self.dispatch_state = "BLOCKED" if self.excess_count else "READY"
        self.recommendation = f"Remove {self.excess_count} package before dispatch" if self.excess_count == 1 else (
            f"Remove {self.excess_count} packages before dispatch" if self.excess_count else "Dispatch can proceed"
        )
        self.snapshot_path = snapshot_path
        self.completed_at = time.time()
        self.status = "COMPLETED"
        self.last_error = None
        return self.summary(confidence_threshold)

    def fail(self, reason: str, confidence_threshold: float) -> dict:
        self.status = "FAILED"
        self.last_error = reason
        self.recommendation = reason
        return self.summary(confidence_threshold)

    def summary(self, confidence_threshold: float = 0.75) -> dict:
        return {
            "provider": "SNAPSHOT_YOLO",
            "configured": True,
            "roi": self.config,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "snapshot_id": self.snapshot_id,
            "snapshot_path": self.snapshot_path,
            "raw_detection_count": self.raw_detection_count,
            "valid_detections": self.valid_detections,
            "detected_package_count": self.count,
            "loaded_packages": self.count,
            "count": self.count,
            "visual_capacity": self.limit,
            "configured_limit": self.limit,
            "configured_package_limit": self.limit,
            "excess_count": self.excess_count,
            "capacity_status": self.capacity_status,
            "dispatch_state": self.dispatch_state,
            "dispatch_allowed": self.dispatch_state == "READY",
            "recommendation": self.recommendation,
            "inspection_type": "SNAPSHOT",
            "confidence_threshold": confidence_threshold,
            "instruction": "Arrange packages inside ROI and press S" if self.status == "READY" else "Press R to clear or S to recapture",
            "last_error": self.last_error,
        }


class HubJourneySession:
    def __init__(
        self,
        time_multiplier: float = 1.0,
        config: dict | None = None,
        baseline_seconds: dict[str, float] | None = None,
    ) -> None:
        self.time_multiplier = time_multiplier
        self.config = config or DEFAULT_HUB_ZONES
        self.baseline_seconds = baseline_seconds or {"ZONE_1": 5.0, "ZONE_2": 8.0, "ZONE_3": 4.0}
        self.session_index = 0
        self.reset()

    @property
    def baseline_total_seconds(self) -> float:
        return sum(float(self.baseline_seconds.get(zone, 0)) for zone in ["ZONE_1", "ZONE_2", "ZONE_3"])

    def reset(self) -> None:
        self.status = "READY"
        self.session_id = None
        self.marker_id = None
        self.started_at = None
        self.stopped_at = None
        self.current_zone = None
        self.previous_zone = None
        self.zone_entered_at = None
        self.zone_durations = {"ZONE_1": 0.0, "ZONE_2": 0.0, "ZONE_3": 0.0}
        self.transition_count = 0
        self.completed = False
        self.last_error = None
        self.last_transition = None
        self.last_risk_level = None

    def _zone_name(self, zone_id: str | None) -> str:
        for zone in self.config.get("zones", []):
            if zone.get("zone_id") == zone_id:
                return zone.get("name") or zone_id or "UNASSIGNED"
        return zone_id or "NONE"

    def zone_for(self, center: list[float], width: int, height: int) -> str | None:
        x_norm = float(center[0]) / max(width, 1)
        for zone in self.config.get("zones", []):
            if "x_min" in zone and "x_max" in zone:
                x_min, x_max = float(zone["x_min"]), float(zone["x_max"])
                if x_min <= x_norm < x_max or (x_max >= 1.0 and x_norm <= x_max):
                    return zone["zone_id"]
            elif zone.get("polygon"):
                if _point_in_polygon(center, _polygon_pixels(zone["polygon"], width, height)):
                    return zone["zone_id"]
        return None

    def _find_active_observation(self, observations: list[dict]) -> dict | None:
        if self.marker_id is None:
            return None
        for obs in observations:
            if _marker_key(obs) == self.marker_id:
                return obs
        return None

    def _find_zone_1_observation(self, observations: list[dict], width: int, height: int) -> dict | None:
        for obs in observations:
            if self.zone_for(obs["center"], width, height) == "ZONE_1":
                return obs
        return None

    def start(self, observations: list[dict], width: int, height: int, provider: str, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        obs = self._find_zone_1_observation(observations, width, height)
        if not obs:
            self.last_error = "PLACE PACKAGE IN ZONE 1"
            return self.summary(provider, now)
        self.session_index += 1
        self.status = "RUNNING"
        self.session_id = f"HUB-JOURNEY-{self.session_index:04d}"
        self.marker_id = _marker_key(obs)
        self.started_at = now
        self.stopped_at = None
        self.current_zone = "ZONE_1"
        self.previous_zone = None
        self.zone_entered_at = now
        self.zone_durations = {"ZONE_1": 0.0, "ZONE_2": 0.0, "ZONE_3": 0.0}
        self.transition_count = 0
        self.completed = False
        self.last_error = None
        self.last_transition = None
        return self.summary(provider, now)

    def update(self, observations: list[dict], width: int, height: int, provider: str, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        self.last_transition = None
        if self.status != "RUNNING":
            return self.summary(provider, now)
        obs = self._find_active_observation(observations)
        if not obs:
            return self.summary(provider, now)
        zone = self.zone_for(obs["center"], width, height)
        if zone and zone != self.current_zone:
            old_zone = self.current_zone
            if old_zone in self.zone_durations and self.zone_entered_at is not None:
                self.zone_durations[old_zone] += max(0.0, now - self.zone_entered_at) * self.time_multiplier
            self.previous_zone = old_zone
            self.current_zone = zone
            self.zone_entered_at = now
            self.transition_count += 1
            self.last_transition = {"track_id": _display_marker(self.marker_id), "from": old_zone, "to": zone}
        return self.summary(provider, now)

    def stop(self, provider: str = "ARUCO_IDENTITY", now: float | None = None) -> dict:
        now = time.time() if now is None else now
        if self.status == "RUNNING" and self.current_zone in self.zone_durations and self.zone_entered_at is not None:
            self.zone_durations[self.current_zone] += max(0.0, now - self.zone_entered_at) * self.time_multiplier
        if self.status == "RUNNING":
            self.status = "COMPLETED"
            self.completed = True
            self.stopped_at = now
            self.zone_entered_at = now
        return self.summary(provider, now)

    def _live_durations(self, now: float) -> dict[str, float]:
        durations = dict(self.zone_durations)
        if self.status == "RUNNING" and self.current_zone in durations and self.zone_entered_at is not None:
            durations[self.current_zone] += max(0.0, now - self.zone_entered_at) * self.time_multiplier
        return durations

    def _projection(self, durations: dict[str, float]) -> tuple[float | None, float, str]:
        baseline_total = self.baseline_total_seconds
        if baseline_total <= 0:
            return None, 0.0, "LOW"
        if self.status == "READY":
            return None, 0.0, "LOW"
        if self.status == "COMPLETED":
            projected = sum(durations.values())
        elif self.current_zone == "ZONE_1":
            projected = durations["ZONE_1"] * baseline_total / max(self.baseline_seconds["ZONE_1"], 0.001)
        elif self.current_zone == "ZONE_2":
            elapsed = durations["ZONE_1"] + durations["ZONE_2"]
            baseline = self.baseline_seconds["ZONE_1"] + self.baseline_seconds["ZONE_2"]
            projected = elapsed * baseline_total / max(baseline, 0.001)
        else:
            projected = sum(durations.values())
        delay = max(0.0, projected - baseline_total)
        if projected <= baseline_total:
            risk = "LOW"
        elif projected <= baseline_total * 1.25:
            risk = "MODERATE"
        elif projected <= baseline_total * 1.50:
            risk = "HIGH"
        else:
            risk = "CRITICAL"
        return projected, delay, risk

    def summary(self, provider: str = "ARUCO_IDENTITY", now: float | None = None) -> dict:
        now = time.time() if now is None else now
        durations = self._live_durations(now)
        projected, delay, risk = self._projection(durations)
        actual_total = sum(durations.values())
        final_delay = max(0.0, actual_total - self.baseline_total_seconds) if self.status == "COMPLETED" else None
        risk_changed = risk != self.last_risk_level
        self.last_risk_level = risk
        return {
            "provider": provider,
            "configured": True,
            "zones": self.config.get("zones", []),
            "session_id": self.session_id,
            "status": self.status,
            "journey_status": self.status,
            "marker_id": _display_marker(self.marker_id) if self.marker_id else None,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "current_zone": self.current_zone or "NONE",
            "current_stage": self._zone_name(self.current_zone),
            "previous_zone": self.previous_zone,
            "zone_1_seconds": round(durations["ZONE_1"], 1),
            "zone_2_seconds": round(durations["ZONE_2"], 1),
            "zone_3_seconds": round(durations["ZONE_3"], 1),
            "current_zone_elapsed_seconds": round(max(0.0, now - self.zone_entered_at) * self.time_multiplier, 1) if self.status == "RUNNING" and self.zone_entered_at is not None else 0,
            "actual_elapsed_seconds": round(actual_total, 1),
            "actual_total_seconds": round(actual_total, 1) if self.status == "COMPLETED" else None,
            "baseline_zone_1_seconds": self.baseline_seconds["ZONE_1"],
            "baseline_zone_2_seconds": self.baseline_seconds["ZONE_2"],
            "baseline_zone_3_seconds": self.baseline_seconds["ZONE_3"],
            "baseline_total_seconds": round(self.baseline_total_seconds, 1),
            "projected_total_seconds": round(projected, 1) if projected is not None else None,
            "estimated_delay_seconds": round(delay, 1),
            "final_delay_seconds": round(final_delay, 1) if final_delay is not None else None,
            "sla_risk_level": risk,
            "transition_count": self.transition_count,
            "completed": self.completed,
            "last_error": self.last_error,
            "instruction": "Place package in Receiving and press S" if self.status == "READY" else "Move package through zones, press X to stop",
            "last_transition": self.last_transition,
            "risk_changed": risk_changed,
            "track_states": [{
                "track_id": _display_marker(self.marker_id) if self.marker_id else None,
                "current_zone": self.current_zone or "NONE",
                "current_stage": self._zone_name(self.current_zone),
                "previous_zone": self.previous_zone,
                "zone_1_seconds": round(durations["ZONE_1"], 1),
                "zone_2_seconds": round(durations["ZONE_2"], 1),
                "zone_3_seconds": round(durations["ZONE_3"], 1),
                "projected_total_seconds": round(projected, 1) if projected is not None else None,
                "estimated_delay_seconds": round(delay, 1),
                "sla_risk_level": risk,
                "transition_count": self.transition_count,
                "journey_status": self.status,
            }] if self.marker_id else [],
            "zone_counts": {self.current_zone: 1} if self.current_zone and self.current_zone != "NONE" else {},
            "changed": bool(self.last_transition or risk_changed),
        }


LoadingState = LoadingInspectionState
HubState = HubJourneySession
