from __future__ import annotations

import json
from pathlib import Path

from cv_worker.config import ROOT


class MarkerReader:
    def __init__(self) -> None:
        import cv2  # type: ignore
        self.cv2 = cv2
        manifest_path = ROOT / "data" / "demo_markers" / "manifest.json"
        self.manifest = {}
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.manifest = {int(item["marker_id"]): item for item in data.get("markers", [])}
        self.enabled = hasattr(cv2, "aruco")
        self.dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50) if self.enabled else None
        self.parameters = cv2.aruco.DetectorParameters() if self.enabled else None
        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.parameters) if self.enabled and hasattr(cv2.aruco, "ArucoDetector") else None

    def scan(self, frame) -> list[dict]:
        if not self.enabled:
            return []
        if self.detector is not None:
            corners, ids, _ = self.detector.detectMarkers(frame)
        else:
            corners, ids, _ = self.cv2.aruco.detectMarkers(frame, self.dictionary, parameters=self.parameters)
        if ids is None:
            return []
        observations = []
        for marker_corners, marker_id_arr in zip(corners, ids):
            marker_id = int(marker_id_arr[0])
            pts = marker_corners[0]
            xs = [float(p[0]) for p in pts]
            ys = [float(p[1]) for p in pts]
            center = [sum(xs) / len(xs), sum(ys) / len(ys)]
            meta = self.manifest.get(marker_id, {})
            observations.append({
                "marker_id": marker_id,
                "track_id": f"MARKER-{marker_id}",
                "shipment_id": meta.get("shipment_id"),
                "package_id": meta.get("package_id"),
                "intended_module": meta.get("intended_module"),
                "bbox": [min(xs), min(ys), max(xs), max(ys)],
                "center": center,
                "corners": pts.tolist(),
                "confidence": 1.0,
                "source": "ARUCO",
            })
        return observations
