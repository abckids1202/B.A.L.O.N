from __future__ import annotations

import time
from datetime import datetime, timezone

from cv_worker.camera_manager import CameraManager
from cv_worker.config import config
from cv_worker.detectors.marker_reader import MarkerReader
from cv_worker.detectors.package_yolo import detect_packages
from cv_worker.detectors.qr_reader import QRReader
from cv_worker.model_registry import damage_model, package_model, registry
from cv_worker.services.event_client import EventClient
from cv_worker.tracking.marker_logic import HubState, LoadingState


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
        self.event_client = EventClient(config.backend_url)
        self.qr_reader = QRReader()
        self.marker_reader = MarkerReader()
        self.loading_state = LoadingState(limit=5)
        self.hub_state = HubState(time_multiplier=config.demo_time_multiplier)
        self.active_context_name = "WRONG"
        self.active_context = CONTEXTS[self.active_context_name]
        self.latest_analysis: dict = {"detections": [], "qr": None, "markers": [], "loading": {}, "hub": {}, "damage": None}
        self._last_inference_at = 0.0
        self._last_qr_emit: dict[str, float] = {}
        self._last_loading_count: int | None = None
        self._last_hub_level: str | None = None

    def set_backend_url(self, backend_url: str) -> None:
        self.event_client.stop()
        self.event_client = EventClient(backend_url)

    def set_loading_context(self, name: str) -> None:
        if name in CONTEXTS:
            self.active_context_name = name
            self.active_context = CONTEXTS[name]

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
        loading = self.loading_state.update(markers, width)
        hub = self.hub_state.update(markers, width, height)
        self.latest_analysis = {"detections": detections, "qr": qr, "markers": markers, "loading": loading, "hub": hub, "damage": self.latest_analysis.get("damage")}
        if not run_model:
            self.inference_latency_ms = (time.perf_counter() - started) * 1000
        if self.mode == "DISPATCH_VALIDATION" and qr:
            self._maybe_emit_dispatch(qr)
        elif self.mode == "LOADING_COMPLIANCE":
            self._maybe_emit_loading(loading)
        elif self.mode == "HUB_VISION":
            self._maybe_emit_hub(hub)

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
        expected_vehicle = "VAN-021" if shipment_id == "SHP-LOAD-001" else self.active_context.get("current_vehicle_id")
        observed = self.active_context["current_vehicle_id"]
        valid = observed == expected_vehicle
        event_type = "PACKAGE_LOADING_VALIDATED" if valid else "PACKAGE_LOADING_MISMATCH"
        self.emit_material_event(event_type, shipment_id=shipment_id, package_id=package_id, vehicle_id=observed, payload={
            "qr_payload": payload,
            "loading_context": self.active_context,
            "expected_vehicle_id": expected_vehicle,
            "observed_vehicle_id": observed,
            "validation_result": "VALID" if valid else "WRONG_VEHICLE",
            "dispatch_state": "DISPATCH_READY" if valid else "DISPATCH_BLOCKED",
        }, severity="INFO" if valid else "CRITICAL", confidence=0.96)

    def _maybe_emit_loading(self, loading: dict) -> None:
        count = int(loading.get("loaded_packages", 0))
        if self._last_loading_count == count:
            return
        self._last_loading_count = count
        self.emit_material_event("LOAD_COMPLIANCE_UPDATED", vehicle_id=self.active_context["current_vehicle_id"], payload=loading, severity="MEDIUM" if not loading.get("dispatch_allowed", True) else "INFO", confidence=0.86)

    def _maybe_emit_hub(self, hub: dict) -> None:
        level = hub.get("congestion_level")
        if self._last_hub_level == level and not hub.get("changed"):
            return
        self._last_hub_level = level
        self.emit_material_event("HUB_VISUAL_CONGESTION_CHANGED", hub_id="HUB-JKT", payload={**hub, "observed_packages": sum(hub.get("zone_counts", {}).values())}, severity=level or "INFO", confidence=0.82)

    def emit_material_event(self, event_type: str | None = None, **overrides) -> dict:
        event = self._event_for_mode(event_type, **overrides)
        self.last_event = event
        if not self.backend_enabled:
            self.last_backend_result = {"accepted": False, "delivery_status": "DISABLED", "backend_disabled": True}
            return self.last_backend_result
        result = self.event_client.send(event)
        self.last_backend_result = result
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
                "active_context": self.active_context,
            },
        }
        base["payload"].update(overrides.get("payload") or {})
        base.update({k: v for k, v in overrides.items() if k in {"shipment_id", "package_id", "vehicle_id", "hub_id"}})
        if event_type:
            return {**base, "event_type": event_type}
        if mode == "PACKAGE_QUALITY":
            shipment_id = qr_payload.get("shipment_id") or "SHP-DMG-001"
            package_id = qr_payload.get("package_id") or "PKG-DMG-001"
            return {**base, "event_type": "PACKAGE_DAMAGE_DETECTED", "shipment_id": shipment_id, "package_id": package_id, "hub_id": "HUB-JKT", "severity": "HIGH"}
        if mode == "DISPATCH_VALIDATION":
            return {**base, "event_type": "PACKAGE_LOADING_MISMATCH", "shipment_id": qr_payload.get("shipment_id") or "SHP-LOAD-001", "package_id": qr_payload.get("package_id") or "PKG-LOAD-001", "vehicle_id": self.active_context["current_vehicle_id"], "hub_id": "HUB-JKT", "severity": "CRITICAL", "payload": {**base["payload"], "observed_vehicle_id": self.active_context["current_vehicle_id"]}}
        if mode == "LOADING_COMPLIANCE":
            loading = self.latest_analysis.get("loading") or {}
            return {**base, "event_type": "LOAD_COMPLIANCE_UPDATED", "vehicle_id": self.active_context["current_vehicle_id"], "hub_id": "HUB-JKT", "payload": {**base["payload"], **loading}}
        hub = self.latest_analysis.get("hub") or {}
        return {**base, "event_type": "HUB_VISUAL_CONGESTION_CHANGED", "hub_id": "HUB-JKT", "severity": hub.get("congestion_level", "MEDIUM"), "payload": {**base["payload"], **hub, "observed_packages": sum(hub.get("zone_counts", {}).values())}}

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
            "tracker_status": "MARKER_IDENTITY" if self.marker_reader.enabled else "ARUCO_UNAVAILABLE",
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
            "last_event": self.last_event,
            "last_backend_result": last_delivery,
            "delivery_history": list(self.event_client.history),
            "events_emitted": self.events_emitted,
            "source_type": self.camera.source_type,
            "frame_size": {"width": self.camera.frame_width, "height": self.camera.frame_height},
            "latest_analysis": self.latest_analysis,
            "assets": assets,
            "worker_version": "local-cv-desktop-v3",
            "note": "Local webcam owns live CV. Web frontend reads status/events and does not need webcam ownership.",
        }


runtime = CVRuntime()
