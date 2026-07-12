from __future__ import annotations

import json
import time
from pathlib import Path
from datetime import datetime, timezone

from cv_worker.camera_manager import CameraManager
from cv_worker.config import config
from cv_worker.detectors.marker_reader import MarkerReader
from cv_worker.detectors.package_yolo import detect_packages
from cv_worker.detectors.qr_reader import QRReader
from cv_worker.model_registry import damage_model, package_model, registry
from cv_worker.services.event_client import EventClient
from cv_worker.tracking.centroid_tracker import CentroidTracker
from cv_worker.tracking.marker_logic import DEFAULT_HUB_ZONES, DEFAULT_LOADING_CONFIG, HubJourneySession, LoadingInspectionState, _bbox_iou, _centroid_distance_ratio, make_marker_candidate, make_yolo_candidate


def observed_short(value: str | None) -> str:
    if not value:
        return "--:--:--"
    return str(value).split("T")[-1].split("+")[0].split(".")[0]


HERO_ASSIGNMENTS = {
    "SHP-DMG-001": {"package_id": "PKG-DMG-001", "planned_vehicle_id": "VAN-021", "planned_route_id": "RTE-JKT-BKS-01", "module": "PACKAGE_QUALITY"},
    "SHP-LOAD-001": {"package_id": "PKG-LOAD-001", "planned_vehicle_id": "VAN-021", "planned_route_id": "RTE-JKT-BKS-01", "module": "DISPATCH_VALIDATION"},
    "SHP-LOAD-002": {"package_id": "PKG-LOAD-002", "planned_vehicle_id": "VAN-044", "planned_route_id": "RTE-JKT-TNG-01", "module": "LOADING_COMPLIANCE"},
    "SHP-HUB-001": {"package_id": "PKG-HUB-001", "planned_vehicle_id": "VAN-021", "planned_route_id": "RTE-JKT-BKS-01", "module": "HUB_VISION"},
}

CONTEXTS = {
    "CORRECT": {
        "loading_context_id": "CTX-JKT-BAY-01",
        "hub_id": "HUB-JKT",
        "loading_bay_id": "BAY-01",
        "current_vehicle_id": "VAN-021",
        "current_route_id": "RTE-JKT-BKS-01",
        "current_destination_id": "HUB-BKS",
        "status": "ACTIVE",
    },
    "WRONG": {
        "loading_context_id": "CTX-JKT-BAY-02",
        "hub_id": "HUB-JKT",
        "loading_bay_id": "BAY-02",
        "current_vehicle_id": "VAN-044",
        "current_route_id": "RTE-JKT-TNG-01",
        "current_destination_id": "HUB-TNG",
        "status": "ACTIVE",
    },
}


class CVRuntime:
    def __init__(self) -> None:
        self.mode = "PACKAGE_QUALITY"
        self.camera = CameraManager()
        self.events_emitted = 0
        self.inference_fps = 0.0
        self.inference_latency_ms = 0.0
        self.backend_enabled = config.backend_event_enabled
        self.last_backend_result: dict | None = None
        self.last_event: dict | None = None
        self.mode_events: dict[str, dict | None] = {}
        self.mode_backend_results: dict[str, dict | None] = {}
        self.event_timeline: list[dict] = []
        self.event_client = EventClient(config.backend_url)
        self.qr_reader = QRReader()
        self.marker_reader = MarkerReader()
        self.loading_state = LoadingInspectionState(limit=5, config=self._load_json_config("config/cv/loading_roi.json", DEFAULT_LOADING_CONFIG))
        self.hub_state = HubJourneySession(time_multiplier=config.demo_time_multiplier, config=self._load_json_config("config/cv/hub_zones.json", DEFAULT_HUB_ZONES), demo_baseline_seconds=config.hub_demo_baseline_seconds, real_baseline_hours=config.hub_real_baseline_hours)
        self.yolo_tracker = CentroidTracker()
        self.active_context_name = "WRONG"
        self.active_context = CONTEXTS[self.active_context_name]
        self.latest_analysis: dict = {"detections": [], "qr": None, "markers": [], "tracking_observations": [], "tracking_provider": "NONE", "loading": {}, "hub": {}, "damage": None}
        self._last_inference_at = 0.0
        self._last_qr_emit: dict[str, float] = {}
        self._last_loading_count: int | None = None
        self._last_hub_level: str | None = None
        self._last_hub_risk_event: str | None = None
        self._last_hub_projection_bucket: int | None = None
        self._hub_yolo_history: list[list[dict]] = []
        self.last_emit_error: str | None = None


    def _load_json_config(self, rel_path: str, fallback: dict) -> dict:
        path = Path(__file__).resolve().parents[1] / rel_path
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return fallback

    def _configured_tracking_provider(self) -> str:
        if self.mode == "LOADING_COMPLIANCE":
            return config.loading_tracking_provider
        if self.mode == "HUB_VISION":
            return config.hub_tracking_provider
        return "auto"

    def _tracking_observations(self, markers: list[dict], detections: list[dict]) -> tuple[str, list[dict]]:
        configured = self._configured_tracking_provider()
        if configured in {"aruco", "marker", "markers"}:
            if markers:
                return "ARUCO_IDENTITY", markers
            return "ARUCO_WAITING_FOR_MARKER", []
        if configured == "yolo_centroid":
            yolo_tracks = self.yolo_tracker.update(detections)
            return ("YOLO_CENTROID_FALLBACK", yolo_tracks) if yolo_tracks else ("NO_TRACKS", [])
        if configured == "bytetrack":
            return "BYTETRACK_UNAVAILABLE_FALLING_BACK", []
        if markers:
            return "ARUCO_IDENTITY", markers
        yolo_tracks = self.yolo_tracker.update(detections)
        if yolo_tracks:
            return "YOLO_CENTROID_FALLBACK", yolo_tracks
        return "NO_TRACKS", []

    def reset_active_module(self) -> None:
        if self.mode == "LOADING_COMPLIANCE":
            self.loading_state.reset()
            self.yolo_tracker = CentroidTracker()
            self._last_loading_count = None
        elif self.mode == "HUB_VISION":
            self.hub_state.reset()
            self.yolo_tracker = CentroidTracker()
            self._last_hub_level = None
            self._last_hub_risk_event = None
            self._last_hub_projection_bucket = None
        elif self.mode == "DISPATCH_VALIDATION":
            self._last_qr_emit.clear()
        self.last_event = None
        self.last_backend_result = None
        self.mode_events.pop(self.mode, None)
        self.mode_backend_results.pop(self.mode, None)
        self.event_timeline = [item for item in self.event_timeline if item.get("module") != self.mode]
        self.last_emit_error = None
        self.latest_analysis.update({"tracking_observations": [], "tracking_provider": "NONE", "loading": self.loading_state.summary(config.confidence_threshold), "hub": self.hub_state.summary()})

    def set_backend_url(self, backend_url: str) -> None:
        self.event_client.stop()
        self.event_client = EventClient(backend_url)

    def set_loading_context(self, name: str) -> None:
        if name in CONTEXTS:
            self.active_context_name = name
            self.active_context = CONTEXTS[name]
            # Changing context is a new validation decision, so allow immediate rescan.
            self._last_qr_emit.clear()

    def analyze_frame(self, frame) -> None:
        started = time.perf_counter()
        now = time.perf_counter()
        run_model = now - self._last_inference_at >= 1 / max(config.target_inference_fps, 0.5)
        detections = self.latest_analysis.get("detections", [])
        if run_model:
            self._last_inference_at = now
            model = package_model()
            result = detect_packages(model, frame, config.confidence_threshold)
            detections = result.get("detections", [])
            self.inference_latency_ms = result.get("processing_time_ms", 0.0)
            self.inference_fps = 1000 / self.inference_latency_ms if self.inference_latency_ms else 0.0
        qr = self.qr_reader.scan(frame)
        markers = self.marker_reader.scan(frame)
        height, width = frame.shape[:2]
        tracking_provider, observations = self._tracking_observations(markers, detections)
        if self.mode == "HUB_VISION":
            self._record_hub_yolo_history(detections)
            hub_candidate = self._resolve_hub_candidate(markers, detections, width, height, require_zone_1=False)
            if hub_candidate:
                tracking_provider = hub_candidate["source"]
                observations = [hub_candidate]
        else:
            hub_candidate = None
        loading = self.loading_state.summary(config.confidence_threshold)
        hub = self.hub_state.update(hub_candidate, width, height, tracking_provider) if self.mode == "HUB_VISION" else self.hub_state.summary(tracking_provider)
        if self.mode == "HUB_VISION" and hub_candidate and hub.get("status") == "READY":
            hub["candidate"] = hub_candidate
            hub["start_candidate"] = hub_candidate
        self.latest_analysis = {"detections": detections, "qr": qr, "markers": markers, "tracking_observations": observations, "tracking_provider": tracking_provider, "loading": loading, "hub": hub, "damage": self.latest_analysis.get("damage")}
        if not run_model:
            self.inference_latency_ms = (time.perf_counter() - started) * 1000
        if self.mode == "DISPATCH_VALIDATION" and qr:
            self._maybe_emit_dispatch(qr)
        elif self.mode == "HUB_VISION":
            self._maybe_emit_hub(hub)

    def start_active_module(self, frame=None) -> dict:
        if self.mode == "LOADING_COMPLIANCE":
            return self.capture_loading_snapshot(frame)
        self.last_emit_error = "S captures Loading snapshots only. Use H to start Hub journeys."
        return {"accepted": False, "delivery_status": "NOT_READY", "error": self.last_emit_error}

    def start_hub_module(self, frame=None) -> dict:
        if self.mode == "HUB_VISION":
            return self.start_hub_journey(frame)
        self.last_emit_error = "H starts Hub journeys only."
        return {"accepted": False, "delivery_status": "NOT_READY", "error": self.last_emit_error}

    def stop_active_module(self) -> dict:
        if self.mode == "HUB_VISION":
            hub = self.hub_state.stop(self.latest_analysis.get("tracking_provider") or "ARUCO_IDENTITY")
            self.latest_analysis["hub"] = hub
            if hub.get("status") == "COMPLETED":
                return self.emit_material_event("HUB_JOURNEY_COMPLETED", hub_id="HUB-JKT", payload=hub, severity=hub.get("sla_risk_level", "INFO"), confidence=0.9)
            return {"accepted": False, "delivery_status": "NOT_READY", "error": "No running hub journey to stop."}
        self.last_emit_error = "Stop is only used for Hub Vision."
        return {"accepted": False, "delivery_status": "NOT_READY", "error": self.last_emit_error}

    def capture_loading_snapshot(self, frame=None) -> dict:
        frame = frame if frame is not None else self.camera.frame()
        if frame is None:
            loading = self.loading_state.fail("No camera frame available for snapshot.", config.confidence_threshold)
            self.latest_analysis["loading"] = loading
            self.last_emit_error = loading["last_error"]
            return {"accepted": False, "delivery_status": "FAILED", "error": self.last_emit_error}
        started = time.perf_counter()
        model = package_model()
        result = detect_packages(model, frame, config.confidence_threshold)
        self.inference_latency_ms = result.get("processing_time_ms", round((time.perf_counter() - started) * 1000, 2))
        height, width = frame.shape[:2]
        loading = self.loading_state.capture(result.get("detections", []), width, height, config.confidence_threshold)
        self.latest_analysis.update({"detections": result.get("detections", []), "loading": loading, "tracking_provider": "SNAPSHOT_YOLO"})
        event_type = "PROTOTYPE_LOAD_LIMIT_EXCEEDED" if loading["excess_count"] else "LOADING_COMPLIANCE_VALIDATED"
        return self.emit_material_event(event_type, vehicle_id=self.active_context["current_vehicle_id"], hub_id="HUB-JKT", payload=loading, severity="CRITICAL" if loading["excess_count"] else "INFO", confidence=0.9)

    def start_hub_journey(self, frame=None) -> dict:
        frame = frame if frame is not None else self.camera.frame()
        if frame is None:
            self.last_emit_error = "No camera frame available for hub journey start."
            return {"accepted": False, "delivery_status": "FAILED", "error": self.last_emit_error}
        markers = self.marker_reader.scan(frame)
        model = package_model()
        result = detect_packages(model, frame, config.confidence_threshold)
        detections = result.get("detections", [])
        self._record_hub_yolo_history(detections)
        height, width = frame.shape[:2]
        candidate = self._resolve_hub_candidate(markers, detections, width, height, require_zone_1=True)
        provider = candidate["source"] if candidate else config.hub_tracking_provider.upper()
        hub = self.hub_state.start(candidate, width, height, provider)
        self.latest_analysis.update({"detections": detections, "markers": markers, "tracking_observations": [candidate] if candidate else [], "tracking_provider": provider, "hub": hub})
        if hub.get("status") != "RUNNING":
            self.last_emit_error = hub.get("last_error") or "Place package in Receiving and press H."
            return {"accepted": False, "delivery_status": "NOT_READY", "error": self.last_emit_error}
        self.last_emit_error = None
        return self.emit_material_event("HUB_JOURNEY_STARTED", hub_id="HUB-JKT", payload=hub, severity="INFO", confidence=0.9)

    def _package_detections(self, detections: list[dict]) -> list[dict]:
        return [
            item for item in detections
            if item.get("normalized_class") == "PACKAGE" and float(item.get("confidence", 0)) >= config.confidence_threshold
        ]

    def _record_hub_yolo_history(self, detections: list[dict]) -> None:
        self._hub_yolo_history.append(self._package_detections(detections))
        self._hub_yolo_history = self._hub_yolo_history[-5:]

    def _stable_yolo_frames(self, detection: dict, width: int, height: int) -> int:
        count = 0
        centroid = detection.get("centroid")
        bbox = detection.get("bbox")
        for frame_detections in self._hub_yolo_history[-5:]:
            for candidate in frame_detections:
                if _bbox_iou(candidate.get("bbox", []), bbox) >= 0.25 or _centroid_distance_ratio(candidate.get("centroid", [0, 0]), centroid, width, height) <= 0.15:
                    count += 1
                    break
        return count

    def _marker_start_candidate(self, markers: list[dict], width: int, height: int, require_zone_1: bool) -> dict | None:
        for marker in markers:
            zone = self.hub_state.zone_for(marker.get("center", [0, 0]), width, height)
            if require_zone_1 and zone != "ZONE_1":
                continue
            return make_marker_candidate(marker, zone=zone)
        return None

    def _yolo_start_candidate(self, detections: list[dict], width: int, height: int, require_zone_1: bool) -> dict | None:
        packages = self._package_detections(detections)
        if self.hub_state.status == "RUNNING" and self.hub_state.provider == "YOLO_SINGLE_PACKAGE":
            matches = []
            for item in packages:
                if not self.hub_state.locked_bbox or not self.hub_state.locked_centroid:
                    continue
                iou = _bbox_iou(item.get("bbox", []), self.hub_state.locked_bbox)
                distance = _centroid_distance_ratio(item.get("centroid", [0, 0]), self.hub_state.locked_centroid, width, height)
                if iou >= 0.25 or distance <= 0.15:
                    matches.append((iou - distance, item))
            if matches:
                item = sorted(matches, key=lambda row: row[0], reverse=True)[0][1]
                zone = self.hub_state.zone_for(item.get("centroid", [0, 0]), width, height)
                return make_yolo_candidate(item, zone=zone, stable_frames=self._stable_yolo_frames(item, width, height), identity=self.hub_state.identity or "YOLO-PACKAGE-01")
            return None
        candidates = []
        for item in packages:
            zone = self.hub_state.zone_for(item.get("centroid", [0, 0]), width, height)
            if require_zone_1 and zone != "ZONE_1":
                continue
            stable = self._stable_yolo_frames(item, width, height)
            if require_zone_1 and stable < 3:
                continue
            candidates.append(make_yolo_candidate(item, zone=zone, stable_frames=stable))
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: (item.get("stable_frames", 0), item.get("confidence", 0)), reverse=True)[0]

    def _resolve_hub_candidate(self, markers: list[dict], detections: list[dict], width: int, height: int, require_zone_1: bool = False) -> dict | None:
        configured = config.hub_tracking_provider.lower()
        marker = self._marker_start_candidate(markers, width, height, require_zone_1)
        yolo = self._yolo_start_candidate(detections, width, height, require_zone_1)
        if configured in {"aruco", "marker", "markers"}:
            return marker
        if configured in {"yolo", "yolo_single_package"}:
            return yolo
        return marker or yolo

    def analyze_damage(self, frame) -> dict:
        detector = damage_model()
        if detector is None:
            self.latest_analysis["damage"] = {"status": "UNAVAILABLE", "error": registry()["damage"].get("error") or registry()["damage"].get("status")}
            return self.latest_analysis["damage"]
        detections = self.latest_analysis.get("detections") or []
        crop = frame
        if detections:
            x1, y1, x2, y2 = [int(v) for v in detections[0]["bbox"]]
            h, w = frame.shape[:2]
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
            if x2 > x1 and y2 > y1:
                crop = frame[y1:y2, x1:x2]
        result = detector.predict(crop)
        self.latest_analysis["damage"] = result
        if result.get("label") == "DAMAGED" and result.get("confidence", 0) >= 0.65:
            self.emit_material_event("PACKAGE_DAMAGE_DETECTED")
        return result

    def _maybe_emit_dispatch(self, qr: dict) -> None:
        payload = qr.get("payload") or {}
        shipment_id = payload.get("shipment_id")
        package_id = payload.get("package_id")
        if not shipment_id:
            return
        key = f"{shipment_id}:{self.active_context_name}"
        now = time.time()
        if now - self._last_qr_emit.get(key, 0) < 3:
            return
        self._last_qr_emit[key] = now
        assignment = HERO_ASSIGNMENTS.get(shipment_id, {})
        expected_vehicle = assignment.get("planned_vehicle_id")
        expected_route = assignment.get("planned_route_id")
        observed = self.active_context["current_vehicle_id"]
        active_route = self.active_context["current_route_id"]
        valid = bool(expected_vehicle) and observed == expected_vehicle and (not expected_route or active_route == expected_route)
        event_type = "PACKAGE_LOADING_VALIDATED" if valid else "PACKAGE_LOADING_MISMATCH"
        self.emit_material_event(event_type, shipment_id=shipment_id, package_id=package_id or assignment.get("package_id"), vehicle_id=observed, payload={
            "qr_payload": payload,
            "loading_context": self.active_context,
            "expected_vehicle_id": expected_vehicle,
            "expected_route_id": expected_route,
            "observed_vehicle_id": observed,
            "active_route_id": active_route,
            "recommended_dispatch_qr": "SHP-LOAD-001",
            "validation_result": "VALID" if valid else "WRONG_VEHICLE",
            "dispatch_state": "DISPATCH_READY" if valid else "DISPATCH_BLOCKED",
        }, severity="INFO" if valid else "CRITICAL", confidence=0.96)

    def _maybe_emit_loading(self, loading: dict) -> None:
        return

    def _maybe_emit_hub(self, hub: dict) -> None:
        if hub.get("status") != "RUNNING":
            return
        transition = hub.get("last_transition")
        if transition:
            event_type = "HUB_PACKAGE_MOVED_TO_PROCESSING" if transition.get("to") == "ZONE_2" else "HUB_PACKAGE_MOVED_TO_DISPATCH" if transition.get("to") == "ZONE_3" else None
            if event_type:
                self.emit_material_event(event_type, hub_id="HUB-JKT", payload=hub, severity=hub.get("sla_risk_level", "INFO"), confidence=0.88)
        risk = hub.get("sla_risk_level")
        if risk and risk != self._last_hub_risk_event:
            self._last_hub_risk_event = risk
            self.emit_material_event("HUB_DELAY_RISK_LEVEL_CHANGED", hub_id="HUB-JKT", payload=hub, severity=risk, confidence=0.84)
        projected = hub.get("projected_real_dwell_hours")
        if projected is not None:
            bucket = int(float(projected) // 10)
            if bucket != self._last_hub_projection_bucket:
                self._last_hub_projection_bucket = bucket
                self.emit_material_event("HUB_PROJECTED_DWELL_UPDATED", hub_id="HUB-JKT", payload=hub, severity=risk or "INFO", confidence=0.82)

    def emit_material_event(self, event_type: str | None = None, **overrides) -> dict:
        event = self._event_for_mode(event_type, **overrides)
        if event.get("event_type") == "CANNOT_EMIT":
            self.last_emit_error = event.get("payload", {}).get("reason", "Cannot emit yet")
            self.last_backend_result = {"accepted": False, "delivery_status": "NOT_READY", "error": self.last_emit_error}
            return self.last_backend_result
        self.last_emit_error = None
        self.last_event = event
        self.mode_events[event.get("module", self.mode)] = event
        self.event_timeline.append({"time": observed_short(event.get("observed_at")), "module": event.get("module"), "event": event.get("event_type"), "status": event.get("payload", {}).get("dispatch_state") or event.get("payload", {}).get("status") or event.get("severity")})
        self.event_timeline = self.event_timeline[-8:]
        if not self.backend_enabled:
            self.last_backend_result = {"accepted": False, "delivery_status": "DISABLED", "backend_disabled": True}
            self.mode_backend_results[event.get("module", self.mode)] = self.last_backend_result
            return self.last_backend_result
        result = self.event_client.send(event)
        self.last_backend_result = result
        self.mode_backend_results[event.get("module", self.mode)] = result
        self.events_emitted += 1
        return result

    def _event_for_mode(self, event_type: str | None = None, **overrides) -> dict:
        observed_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        mode = self.mode.upper()
        detections = self.latest_analysis.get("detections") or []
        qr = self.latest_analysis.get("qr") or {}
        qr_payload = qr.get("payload") or {}
        base = {
            "event_id": f"CVE-DESKTOP-{mode}-{int(time.time() * 1000)}",
            "module": mode,
            "source": "LOCAL_CV_WORKER",
            "camera_id": config.camera_id,
            "observed_at": observed_at,
            "demo_time": observed_at,
            "confidence": float(overrides.get("confidence", detections[0]["confidence"] if detections else 0.82)),
            "severity": overrides.get("severity", "MEDIUM"),
            "model_name": "local_cv_runtime",
            "model_version": "desktop-v3",
            "processing_time_ms": round(self.inference_latency_ms, 2),
            "payload": {
                "detections": detections[:5],
                "qr": qr_payload,
                "markers": self.latest_analysis.get("markers", [])[:10],
                "tracking_observations": self.latest_analysis.get("tracking_observations", [])[:10],
                "tracking_provider": self.latest_analysis.get("tracking_provider"),
                "active_context": self.active_context,
            },
        }
        base["payload"].update(overrides.get("payload") or {})
        base.update({k: v for k, v in overrides.items() if k in {"shipment_id", "package_id", "vehicle_id", "hub_id"}})
        if event_type:
            return {**base, "event_type": event_type}
        if mode == "DISPATCH_VALIDATION" and not qr_payload.get("shipment_id"):
            return {**base, "event_type": "CANNOT_EMIT", "payload": {**base["payload"], "reason": "Cannot emit: scan a QR first."}}
        if mode == "LOADING_COMPLIANCE" and (self.latest_analysis.get("loading") or {}).get("status") != "COMPLETED":
            return {**base, "event_type": "CANNOT_EMIT", "payload": {**base["payload"], "reason": "Cannot emit: press S to capture a loading snapshot first."}}
        if mode == "HUB_VISION" and (self.latest_analysis.get("hub") or {}).get("status") == "READY":
            return {**base, "event_type": "CANNOT_EMIT", "payload": {**base["payload"], "reason": "Cannot emit: press H to start a hub journey first."}}
        if mode == "PACKAGE_QUALITY":
            shipment_id = qr_payload.get("shipment_id") or "SHP-DMG-001"
            package_id = qr_payload.get("package_id") or "PKG-DMG-001"
            return {**base, "event_type": "PACKAGE_DAMAGE_DETECTED", "shipment_id": shipment_id, "package_id": package_id, "hub_id": "HUB-JKT", "severity": "HIGH"}
        if mode == "DISPATCH_VALIDATION":
            return {**base, "event_type": "PACKAGE_LOADING_MISMATCH", "shipment_id": qr_payload.get("shipment_id") or "SHP-LOAD-001", "package_id": qr_payload.get("package_id") or "PKG-LOAD-001", "vehicle_id": self.active_context["current_vehicle_id"], "hub_id": "HUB-JKT", "severity": "CRITICAL", "payload": {**base["payload"], "observed_vehicle_id": self.active_context["current_vehicle_id"]}}
        if mode == "LOADING_COMPLIANCE":
            loading = self.latest_analysis.get("loading") or {}
            event_name = "PROTOTYPE_LOAD_LIMIT_EXCEEDED" if loading.get("excess_count", 0) else "LOADING_COMPLIANCE_VALIDATED"
            return {**base, "event_type": event_name, "vehicle_id": self.active_context["current_vehicle_id"], "hub_id": "HUB-JKT", "payload": {**base["payload"], **loading}}
        hub = self.latest_analysis.get("hub") or {}
        event_name = "HUB_JOURNEY_COMPLETED" if hub.get("status") == "COMPLETED" else "HUB_PROJECTED_DWELL_UPDATED"
        return {**base, "event_type": event_name, "hub_id": "HUB-JKT", "severity": hub.get("sla_risk_level", "MEDIUM"), "payload": {**base["payload"], **hub}}

    def status(self) -> dict:
        assets = registry()
        last_delivery = self.event_client.last_result or self.last_backend_result
        return {
            "status": "ONLINE",
            "camera_status": self.camera.status,
            "camera_error": self.camera.error,
            "active_mode": self.mode,
            "active_context": self.active_context_name,
            "active_loading_context": self.active_context,
            "package_model_status": assets["package"]["status"],
            "damage_model_status": assets["damage"]["status"],
            "package_provider": assets["package"]["provider"],
            "damage_provider": assets["damage"]["provider"],
            "qr_status": "READY",
            "configured_loading_tracking": config.loading_tracking_provider.upper(),
            "configured_hub_tracking": config.hub_tracking_provider.upper(),
            "tracker_status": self.latest_analysis.get("tracking_provider") or ("ARUCO_AVAILABLE" if self.marker_reader.enabled else "ARUCO_UNAVAILABLE"),
            "backend_connected": self.backend_enabled and self.event_client.delivery_status != "FAILED",
            "backend_enabled": self.backend_enabled,
            "delivery_status": self.event_client.delivery_status,
            "pending_events": self.event_client.queue.qsize(),
            "delivered_events": self.event_client.delivered_event_count,
            "failed_events": self.event_client.failed_event_count,
            "camera_fps": self.camera.camera_fps,
            "inference_fps": self.inference_fps,
            "latency_ms": self.inference_latency_ms,
            "last_event_at": self.event_client.last_success_at,
            "last_event": self.mode_events.get(self.mode) or self.last_event,
            "last_backend_result": self.mode_backend_results.get(self.mode) or last_delivery,
            "event_timeline": self.event_timeline,
            "delivery_history": list(self.event_client.history),
            "events_emitted": self.events_emitted,
            "source_type": self.camera.source_type,
            "frame_size": {"width": self.camera.frame_width, "height": self.camera.frame_height},
            "latest_analysis": self.latest_analysis,
            "assets": assets,
            "last_emit_error": self.last_emit_error,
            "worker_version": "local-cv-desktop-v5-snapshot-journey",
            "note": "Local webcam owns live CV. Web frontend reads status/events and does not need webcam ownership.",
        }


runtime = CVRuntime()

