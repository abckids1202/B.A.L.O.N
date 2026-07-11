from __future__ import annotations

from cv_worker.camera_manager import CameraManager
from cv_worker.config import config
from cv_worker.model_registry import registry
from cv_worker.services.event_client import EventClient


class CVRuntime:
    def __init__(self) -> None:
        self.mode = "IDLE"
        self.camera = CameraManager()
        self.events_emitted = 0
        self.inference_fps = 0.0
        self.inference_latency_ms = 0.0
        self.event_client = EventClient()

    def status(self) -> dict:
        assets = registry()
        return {
            "status": "ONLINE",
            "camera_status": self.camera.status,
            "active_mode": self.mode,
            "package_model_status": assets["package"]["status"],
            "damage_model_status": assets["damage"]["status"],
            "tracker_status": "READY",
            "backend_connected": self.event_client.failed_event_count == 0,
            "camera_fps": self.camera.camera_fps,
            "inference_fps": self.inference_fps,
            "latency_ms": self.inference_latency_ms,
            "last_event_at": self.event_client.last_success_at,
            "assets": assets,
            "worker_version": "local-cv-worker-v1",
            "note": "Real YOLO inference starts after local .pt/.onnx weights and optional CV dependencies are installed.",
        }


runtime = CVRuntime()
