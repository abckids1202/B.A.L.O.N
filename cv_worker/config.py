from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class WorkerConfig:
    backend_url: str = os.getenv("CV_BACKEND_URL", "http://127.0.0.1:8000")
    camera_index: int = int(os.getenv("CV_CAMERA_INDEX", "0"))
    camera_width: int = int(os.getenv("CV_CAMERA_WIDTH", "1280"))
    camera_height: int = int(os.getenv("CV_CAMERA_HEIGHT", "720"))
    target_inference_fps: float = float(os.getenv("CV_TARGET_INFERENCE_FPS", "10"))
    display_fps: float = float(os.getenv("CV_DISPLAY_FPS", "20"))
    confidence_threshold: float = float(os.getenv("CV_CONFIDENCE_THRESHOLD", "0.25"))
    worker_port: int = int(os.getenv("CV_WORKER_PORT", "8765"))
    camera_id: str = os.getenv("CV_CAMERA_ID", "CAM-DEMO-01")
    device: str = os.getenv("CV_DEVICE", "auto")


config = WorkerConfig()
