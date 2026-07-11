from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def event(event_type: str, module: str, **kwargs) -> dict:
    now = datetime.now(timezone.utc).astimezone().isoformat()
    return {
        "event_id": kwargs.pop("event_id", f"CVE-{uuid4().hex[:16].upper()}"),
        "event_type": event_type,
        "module": module,
        "source": kwargs.pop("source", "LOCAL_CV_WORKER"),
        "camera_id": kwargs.pop("camera_id", "CAM-DEMO-01"),
        "observed_at": kwargs.pop("observed_at", now),
        "demo_time": kwargs.pop("demo_time", now),
        "confidence": kwargs.pop("confidence", 0.8),
        "severity": kwargs.pop("severity", "INFO"),
        "model_name": kwargs.pop("model_name", "balon-local-cv-worker"),
        "model_version": kwargs.pop("model_version", "worker-v1"),
        "processing_time_ms": kwargs.pop("processing_time_ms", 0),
        "payload": kwargs.pop("payload", {}),
        **kwargs,
    }
