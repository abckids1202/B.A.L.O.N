from __future__ import annotations

import time
from typing import Any

import numpy as np


def detect_packages(model: Any, frame: np.ndarray, confidence: float = 0.25, imgsz: int | None = None) -> dict:
    if model is None:
        return {"detections": [], "processing_time_ms": 0.0, "error": "package model unavailable"}
    started = time.perf_counter()
    predict_kwargs = {"conf": confidence, "verbose": False}
    if imgsz:
        predict_kwargs["imgsz"] = imgsz
    results = model.predict(frame, **predict_kwargs)
    detections = []
    for result in results:
        names = getattr(result, "names", {}) or getattr(model, "names", {}) or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            xyxy = [float(v) for v in box.xyxy[0].tolist()]
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            raw = str(names.get(cls_id, f"class_{cls_id}"))
            x1, y1, x2, y2 = xyxy
            detections.append({
                "raw_class": raw,
                "normalized_class": "PACKAGE" if raw in {"Regular_Box", "Large_Box"} else raw.upper(),
                "confidence": conf,
                "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                "centroid": [round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1)],
            })
    detections.sort(key=lambda item: item["confidence"], reverse=True)
    return {"detections": detections, "processing_time_ms": round((time.perf_counter() - started) * 1000, 2)}
