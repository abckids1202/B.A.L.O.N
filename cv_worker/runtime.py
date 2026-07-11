from __future__ import annotations

import time

from cv_worker.camera_manager import CameraManager
from cv_worker.model_registry import registry
from cv_worker.services.event_client import EventClient


class CVRuntime:
    def __init__(self) -> None:
        self.mode = "PACKAGE_QUALITY"
        self.camera = CameraManager()
        self.events_emitted = 0
        self.inference_fps = 0.0
        self.inference_latency_ms = 0.0
        self.backend_enabled = True
        self.last_backend_result: dict | None = None
        self.last_event: dict | None = None
        self.event_client = EventClient()

    def set_backend_url(self, backend_url: str) -> None:
        self.event_client = EventClient(backend_url)

    def emit_material_event(self) -> dict:
        event = self._event_for_mode()
        self.last_event = event
        if not self.backend_enabled:
            self.last_backend_result = {"accepted": False, "queued": False, "backend_disabled": True}
            return self.last_backend_result
        result = self.event_client.send(event)
        self.last_backend_result = result
        if result.get("accepted"):
            self.events_emitted += 1
        return result

    def _event_for_mode(self) -> dict:
        observed_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        mode = self.mode.upper()
        base = {
            "event_id": f"CVE-DESKTOP-{mode}-{int(time.time() * 1000)}",
            "module": mode,
            "source": "LOCAL_CV_DESKTOP",
            "camera_id": "CAM-DEMO-01",
            "observed_at": observed_at,
            "demo_time": observed_at,
            "confidence": 0.82,
            "severity": "MEDIUM",
            "model_name": "manual-runtime-proof",
            "model_version": "desktop-v1",
            "processing_time_ms": round(self.inference_latency_ms, 2),
            "payload": {"trigger": "keyboard_E", "proof_stage": "raw_camera_event"},
        }
        if mode == "PACKAGE_QUALITY":
            return {**base, "event_type": "PACKAGE_DAMAGE_DETECTED", "shipment_id": "SHP-1028", "package_id": "PKG-1028", "hub_id": "HUB-JKT", "severity": "HIGH", "payload": {**base["payload"], "damage_type": "manual_demo_damage"}}
        if mode == "DISPATCH_VALIDATION":
            return {**base, "event_type": "PACKAGE_LOADING_MISMATCH", "shipment_id": "SHP-1028", "package_id": "PKG-1028", "vehicle_id": "VAN-044", "hub_id": "HUB-JKT", "severity": "CRITICAL", "payload": {**base["payload"], "observed_vehicle_id": "VAN-044", "qr_payload": "SHP-1028"}}
        if mode == "LOADING_COMPLIANCE":
            return {**base, "event_type": "LOAD_COMPLIANCE_UPDATED", "vehicle_id": "TRK-001", "hub_id": "HUB-JKT", "payload": {**base["payload"], "loaded_packages": 6, "visual_capacity": 5, "current_count": 6}}
        return {**base, "event_type": "HUB_VISUAL_CONGESTION_CHANGED", "hub_id": "HUB-JKT", "severity": "HIGH", "payload": {**base["payload"], "observed_packages": 42, "queue_length": 42}}

    def status(self) -> dict:
        assets = registry()
        return {
            "status": "ONLINE",
            "camera_status": self.camera.status,
            "camera_error": self.camera.error,
            "active_mode": self.mode,
            "package_model_status": assets["package"]["status"],
            "damage_model_status": assets["damage"]["status"],
            "qr_status": "READY",
            "tracker_status": "WAITING_FOR_DETECTOR" if assets["package"]["status"] != "LOADED" else "READY",
            "backend_connected": self.backend_enabled and self.event_client.failed_event_count == 0,
            "backend_enabled": self.backend_enabled,
            "camera_fps": self.camera.camera_fps,
            "inference_fps": self.inference_fps,
            "latency_ms": self.inference_latency_ms,
            "last_event_at": self.event_client.last_success_at,
            "last_event": self.last_event,
            "last_backend_result": self.last_backend_result,
            "events_emitted": self.events_emitted,
            "source_type": self.camera.source_type,
            "frame_size": {"width": self.camera.frame_width, "height": self.camera.frame_height},
            "assets": assets,
            "worker_version": "local-cv-desktop-v1",
            "note": "Raw camera and manual material events are active. YOLO inference starts after local .pt/.onnx weights are trained/exported.",
        }


runtime = CVRuntime()
