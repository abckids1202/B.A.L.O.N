from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(ROOT / ".env")
except Exception:
    pass


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class WorkerConfig:
    backend_url: str = os.getenv("CV_BACKEND_URL", "http://127.0.0.1:8000")
    camera_index: int = int(os.getenv("CV_CAMERA_INDEX", "0"))
    camera_width: int = int(os.getenv("CV_CAMERA_WIDTH", "1280"))
    camera_height: int = int(os.getenv("CV_CAMERA_HEIGHT", "720"))
    target_inference_fps: float = float(os.getenv("CV_TARGET_INFERENCE_FPS", "10"))
    display_fps: float = float(os.getenv("CV_DISPLAY_FPS", "20"))
    confidence_threshold: float = float(os.getenv("CV_CONFIDENCE_THRESHOLD", "0.25"))
    worker_host: str = os.getenv("CV_WORKER_HOST", "127.0.0.1")
    worker_port: int = int(os.getenv("CV_WORKER_PORT", "8765"))
    camera_id: str = os.getenv("CV_CAMERA_ID", "CAM-DEMO-01")
    device: str = os.getenv("CV_DEVICE", "auto")
    package_provider: str = os.getenv("CV_PACKAGE_PROVIDER", "local_yolo")
    package_model_path: str = os.getenv("CV_PACKAGE_MODEL_PATH", "models/cv/package_detector/v1/best.pt")
    damage_provider: str = os.getenv("CV_DAMAGE_PROVIDER", "pytorch_classifier")
    damage_model_path: str = os.getenv("CV_DAMAGE_MODEL_PATH", "models/cv/damage_detector/v1/damage_detector.pth")
    tracker: str = os.getenv("CV_TRACKER", "marker_identity")
    event_snapshot_enabled: bool = _bool("CV_EVENT_SNAPSHOT_ENABLED", True)
    backend_event_enabled: bool = _bool("CV_BACKEND_EVENT_ENABLED", True)
    demo_time_multiplier: float = float(os.getenv("CV_DEMO_TIME_MULTIPLIER", "60"))


config = WorkerConfig()
