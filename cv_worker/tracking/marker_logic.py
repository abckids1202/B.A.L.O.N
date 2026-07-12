from __future__ import annotations

import math
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
    identity = obs.get("identity")
    if identity:
        return str(identity)
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


def _centroid_distance_ratio(a: list[float], b: list[float], width: int, height: int) -> float:
    diagonal = math.hypot(max(width, 1), max(height, 1))
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1])) / diagonal


def make_marker_candidate(marker: dict, zone: str | None = None) -> dict:
    identity = _display_marker(_marker_key(marker))
    return {
        "identity": identity,
        "source": "ARUCO_IDENTITY",
        "bbox": marker.get("bbox"),
        "centroid": marker.get("center"),
        "center": marker.get("center"),
        "zone": zone,
        "confidence": 1.0,
        "stable_frames": int(marker.get("stable_frames", 5) or 5),
        "label": identity,
        "last_seen_at": time.time(),
    }


def make_yolo_candidate(detection: dict, zone: str | None = None, stable_frames: int = 1, identity: str = "YOLO-PACKAGE-01") -> dict:
    return {
        "identity": identity,
        "source": "YOLO_SINGLE_PACKAGE",
        "bbox": detection.get("bbox"),
        "centroid": detection.get("centroid"),
        "center": detection.get("centroid"),
        "zone": zone,
        "confidence": float(detection.get("confidence", 0)),
        "stable_frames": stable_frames,
        "label": detection.get("raw_class") or "PACKAGE",
        "last_seen_at": time.time(),
    }


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
        demo_baseline_seconds: dict[str, float] | None = None,
        real_baseline_hours: dict[str, float] | None = None,
        baseline_seconds: dict[str, float] | None = None,
    ) -> None:
        self.time_multiplier = time_multiplier
        self.config = config or DEFAULT_HUB_ZONES
        self.demo_baseline_seconds = demo_baseline_seconds or baseline_seconds or {"ZONE_1": 10.0, "ZONE_2": 10.0, "ZONE_3": 4.0}
        self.real_baseline_hours = real_baseline_hours or {"ZONE_1": 72.48, "ZONE_2": 72.0, "ZONE_3": 3.5}
        self.session_index = 0
        self.reset()

    @property
    def baseline_total_seconds(self) -> float:
        return sum(float(self.demo_baseline_seconds.get(zone, 0)) for zone in ["ZONE_1", "ZONE_2", "ZONE_3"])

    @property
    def real_baseline_total_hours(self) -> float:
        return sum(float(self.real_baseline_hours.get(zone, 0)) for zone in ["ZONE_1", "ZONE_2", "ZONE_3"])

    def reset(self) -> None:
        self.status = "READY"
        self.session_id = None
        self.identity = None
        self.provider = None
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
        self.locked_bbox = None
        self.locked_centroid = None
        self.target_missing_since = None
        self.paused_at = None
        self.target_status = "NO_TARGET"
        self.start_candidate = None
        self.latest_candidate = None

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

    def _coerce_candidate(self, candidate: dict | list[dict] | None, width: int, height: int, provider: str) -> dict | None:
        if isinstance(candidate, dict) and candidate.get("centroid"):
            result = dict(candidate)
            result["zone"] = result.get("zone") or self.zone_for(result["centroid"], width, height)
            return result
        if isinstance(candidate, list):
            for obs in candidate:
                center = obs.get("center") or obs.get("centroid")
                if not center:
                    continue
                zone = self.zone_for(center, width, height)
                if zone:
                    if provider == "YOLO_SINGLE_PACKAGE" or str(obs.get("source", "")).startswith("YOLO"):
                        return make_yolo_candidate({"bbox": obs.get("bbox"), "centroid": center, "confidence": obs.get("confidence", 1), "raw_class": obs.get("raw_class", "PACKAGE")}, zone=zone)
                    return make_marker_candidate({**obs, "center": center}, zone=zone)
        return None

    def start(self, candidate: dict | list[dict] | None, width: int, height: int, provider: str, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        resolved = self._coerce_candidate(candidate, width, height, provider)
        if not resolved or resolved.get("zone") != "ZONE_1":
            self.last_error = "PLACE PACKAGE IN ZONE 1"
            self.start_candidate = resolved
            return self.summary(provider, now)
        self.session_index += 1
        self.status = "RUNNING"
        self.session_id = f"HUB-JOURNEY-{self.session_index:04d}"
        self.identity = resolved["identity"]
        self.provider = resolved.get("source") or provider
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
        self.locked_bbox = resolved.get("bbox")
        self.locked_centroid = resolved.get("centroid")
        self.target_missing_since = None
        self.paused_at = None
        self.target_status = "LOCKED"
        self.start_candidate = resolved
        self.latest_candidate = resolved
        return self.summary(self.provider, now)

    def update(self, candidate: dict | list[dict] | None, width: int, height: int, provider: str, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        self.last_transition = None
        resolved = self._coerce_candidate(candidate, width, height, provider)
        self.latest_candidate = resolved or self.latest_candidate
        if self.status != "RUNNING":
            return self.summary(provider, now)
        if not resolved:
            if self.target_missing_since is None:
                self.target_missing_since = now
            if now - self.target_missing_since > 0.5 and self.paused_at is None:
                if self.current_zone in self.zone_durations and self.zone_entered_at is not None:
                    self.zone_durations[self.current_zone] += max(0.0, now - self.zone_entered_at) * self.time_multiplier
                self.paused_at = now
                self.target_status = "TARGET TEMPORARILY LOST"
            if now - self.target_missing_since > 1.5:
                self.target_status = "TARGET LOST - STOP OR RESET"
            return self.summary(self.provider or provider, now)
        if self.identity and resolved.get("identity") != self.identity and self.provider == "ARUCO_IDENTITY":
            return self.summary(self.provider, now)
        if self.paused_at is not None:
            self.zone_entered_at = now
            self.paused_at = None
        self.target_missing_since = None
        self.target_status = "LOCKED"
        self.locked_bbox = resolved.get("bbox") or self.locked_bbox
        self.locked_centroid = resolved.get("centroid") or self.locked_centroid
        zone = self.zone_for(resolved["centroid"], width, height)
        if zone and zone != self.current_zone:
            old_zone = self.current_zone
            if old_zone in self.zone_durations and self.zone_entered_at is not None:
                self.zone_durations[old_zone] += max(0.0, now - self.zone_entered_at) * self.time_multiplier
            self.previous_zone = old_zone
            self.current_zone = zone
            self.zone_entered_at = now
            self.transition_count += 1
            self.last_transition = {"track_id": self.identity, "from": old_zone, "to": zone}
        return self.summary(self.provider or provider, now)

    def stop(self, provider: str = "ARUCO_IDENTITY", now: float | None = None) -> dict:
        now = time.time() if now is None else now
        if self.status == "RUNNING" and self.current_zone in self.zone_durations and self.zone_entered_at is not None and self.paused_at is None:
            self.zone_durations[self.current_zone] += max(0.0, now - self.zone_entered_at) * self.time_multiplier
        if self.status == "RUNNING":
            self.status = "COMPLETED"
            self.completed = True
            self.stopped_at = now
            self.zone_entered_at = now
            self.target_status = "COMPLETED"
        return self.summary(self.provider or provider, now)

    def _live_durations(self, now: float) -> dict[str, float]:
        durations = dict(self.zone_durations)
        if self.status == "RUNNING" and self.paused_at is None and self.current_zone in durations and self.zone_entered_at is not None:
            durations[self.current_zone] += max(0.0, now - self.zone_entered_at) * self.time_multiplier
        return durations

    def _stage_factors(self, durations: dict[str, float]) -> dict[str, float]:
        return {
            zone: durations[zone] / max(float(self.demo_baseline_seconds.get(zone, 0)), 0.001)
            for zone in ["ZONE_1", "ZONE_2", "ZONE_3"]
        }

    def _projection(self, durations: dict[str, float]) -> dict:
        real_total = self.real_baseline_total_hours
        factors = self._stage_factors(durations)
        if real_total <= 0 or self.status == "READY":
            projected = real_total
        elif self.current_zone == "ZONE_1" and self.status != "COMPLETED":
            projected = real_total * factors["ZONE_1"]
        elif self.current_zone == "ZONE_2" and self.status != "COMPLETED":
            weighted = (
                self.real_baseline_hours["ZONE_1"] * factors["ZONE_1"]
                + self.real_baseline_hours["ZONE_2"] * factors["ZONE_2"]
            ) / max(self.real_baseline_hours["ZONE_1"] + self.real_baseline_hours["ZONE_2"], 0.001)
            projected = real_total * weighted
        else:
            projected = sum(self.real_baseline_hours[zone] * factors[zone] for zone in ["ZONE_1", "ZONE_2", "ZONE_3"])
        delay = max(0.0, projected - real_total)
        ratio = projected / real_total if real_total else 1.0
        if ratio <= 1.0:
            level = "ON_TIME"
        elif ratio <= 1.10:
            level = "LOW"
        elif ratio <= 1.25:
            level = "MODERATE"
        elif ratio <= 1.50:
            level = "HIGH"
        else:
            level = "CRITICAL"
        score = max(0.0, min(100.0, ((ratio - 1.0) / 0.50) * 100.0))
        return {
            "stage_factors": factors,
            "projected_real_dwell_hours": projected,
            "estimated_delay_hours": delay,
            "delay_ratio": ratio,
            "risk_level": level,
            "risk_score": score,
        }

    def summary(self, provider: str = "ARUCO_IDENTITY", now: float | None = None) -> dict:
        now = time.time() if now is None else now
        durations = self._live_durations(now)
        projection = self._projection(durations)
        actual_total = sum(durations.values())
        risk_changed = projection["risk_level"] != self.last_risk_level
        self.last_risk_level = projection["risk_level"]
        candidate = self.latest_candidate or self.start_candidate
        return {
            "provider": self.provider or provider,
            "active_provider": self.provider or provider,
            "configured": True,
            "zones": self.config.get("zones", []),
            "session_id": self.session_id,
            "status": self.status,
            "journey_status": self.status,
            "marker_id": self.identity,
            "identity": self.identity,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "current_zone": self.current_zone or "NONE",
            "current_stage": self._zone_name(self.current_zone),
            "previous_zone": self.previous_zone,
            "zone_1_seconds": round(durations["ZONE_1"], 1),
            "zone_2_seconds": round(durations["ZONE_2"], 1),
            "zone_3_seconds": round(durations["ZONE_3"], 1),
            "zone_1_demo_seconds": round(durations["ZONE_1"], 1),
            "zone_2_demo_seconds": round(durations["ZONE_2"], 1),
            "zone_3_demo_seconds": round(durations["ZONE_3"], 1),
            "demo_total_seconds": round(actual_total, 1),
            "actual_elapsed_seconds": round(actual_total, 1),
            "actual_total_seconds": round(actual_total, 1) if self.status == "COMPLETED" else None,
            "demo_baseline_zone_1_seconds": self.demo_baseline_seconds["ZONE_1"],
            "demo_baseline_zone_2_seconds": self.demo_baseline_seconds["ZONE_2"],
            "demo_baseline_zone_3_seconds": self.demo_baseline_seconds["ZONE_3"],
            "demo_baseline_total_seconds": round(self.baseline_total_seconds, 1),
            "real_zone_1_hours": self.real_baseline_hours["ZONE_1"],
            "real_zone_2_hours": self.real_baseline_hours["ZONE_2"],
            "real_zone_3_hours": self.real_baseline_hours["ZONE_3"],
            "real_baseline_hours": round(self.real_baseline_total_hours, 2),
            "projected_real_dwell_hours": round(projection["projected_real_dwell_hours"], 1),
            "estimated_delay_hours": round(projection["estimated_delay_hours"], 1),
            "delay_ratio": round(projection["delay_ratio"], 3),
            "risk_level": projection["risk_level"],
            "sla_risk_level": projection["risk_level"],
            "risk_score": round(projection["risk_score"], 1),
            "stage_factor_zone_1": round(projection["stage_factors"]["ZONE_1"], 2),
            "stage_factor_zone_2": round(projection["stage_factors"]["ZONE_2"], 2),
            "stage_factor_zone_3": round(projection["stage_factors"]["ZONE_3"], 2),
            "transition_count": self.transition_count,
            "completed": self.completed,
            "target_status": self.target_status,
            "last_error": self.last_error,
            "instruction": "Press H to start journey" if candidate else "Place package in Receiving",
            "candidate": candidate,
            "start_candidate": candidate,
            "last_transition": self.last_transition,
            "risk_changed": risk_changed,
            "track_states": [{
                "track_id": self.identity,
                "current_zone": self.current_zone or "NONE",
                "current_stage": self._zone_name(self.current_zone),
                "previous_zone": self.previous_zone,
                "zone_1_seconds": round(durations["ZONE_1"], 1),
                "zone_2_seconds": round(durations["ZONE_2"], 1),
                "zone_3_seconds": round(durations["ZONE_3"], 1),
                "projected_real_dwell_hours": round(projection["projected_real_dwell_hours"], 1),
                "estimated_delay_hours": round(projection["estimated_delay_hours"], 1),
                "risk_level": projection["risk_level"],
                "risk_score": round(projection["risk_score"], 1),
                "transition_count": self.transition_count,
                "journey_status": self.status,
            }] if self.identity else [],
            "zone_counts": {self.current_zone: 1} if self.current_zone and self.current_zone != "NONE" else {},
            "changed": bool(self.last_transition or risk_changed),
            "benchmark_note": "Prototype benchmark assumptions derived from Indonesian logistics references; not universal national averages.",
        }


LoadingState = LoadingInspectionState
HubState = HubJourneySession
