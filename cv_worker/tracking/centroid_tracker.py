from __future__ import annotations

import time


class CentroidTracker:
    def __init__(self, max_distance_px: float = 140.0, max_lost_seconds: float = 1.25) -> None:
        self.max_distance_px = max_distance_px
        self.max_lost_seconds = max_lost_seconds
        self.tracks: dict[str, dict] = {}
        self._next_id = 1

    @staticmethod
    def _distance(a: list[float], b: list[float]) -> float:
        return ((float(a[0]) - float(b[0])) ** 2 + (float(a[1]) - float(b[1])) ** 2) ** 0.5

    def update(self, detections: list[dict]) -> list[dict]:
        now = time.time()
        assigned: set[str] = set()
        observations: list[dict] = []
        for detection in detections:
            center = detection.get("centroid")
            if not center:
                continue
            best_id = None
            best_distance = self.max_distance_px
            for track_id, track in self.tracks.items():
                if track_id in assigned:
                    continue
                distance = self._distance(center, track["center"])
                if distance <= best_distance:
                    best_distance = distance
                    best_id = track_id
            if best_id is None:
                best_id = f"YOLO-{self._next_id}"
                self._next_id += 1
                self.tracks[best_id] = {"first_seen_at": now, "frames": 0}
            track = self.tracks[best_id]
            track.update({"center": center, "last_seen_at": now, "frames": int(track.get("frames", 0)) + 1, "detection": detection})
            assigned.add(best_id)
            observations.append({
                "track_id": best_id,
                "shipment_id": None,
                "package_id": None,
                "center": center,
                "bbox": detection.get("bbox"),
                "confidence": detection.get("confidence", 0.0),
                "source": "YOLO_CENTROID",
                "raw_class": detection.get("raw_class"),
                "stable_frames": track["frames"],
            })
        for track_id in list(self.tracks):
            if now - float(self.tracks[track_id].get("last_seen_at", now)) > self.max_lost_seconds:
                self.tracks.pop(track_id, None)
        return observations
