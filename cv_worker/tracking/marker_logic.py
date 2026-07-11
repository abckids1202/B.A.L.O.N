from __future__ import annotations

import time


class LoadingState:
    def __init__(self, limit: int = 5) -> None:
        self.limit = limit
        self.loaded: set[str] = set()
        self.last_status = "READY"

    def update(self, markers: list[dict], frame_width: int) -> dict:
        if frame_width <= 0:
            return self.summary()
        entry_x = frame_width * 0.45
        exit_x = frame_width * 0.25
        for marker in markers:
            track_id = marker["track_id"]
            x = marker["center"][0]
            if x >= entry_x:
                self.loaded.add(track_id)
            elif x <= exit_x and track_id in self.loaded:
                self.loaded.remove(track_id)
        return self.summary()

    def summary(self) -> dict:
        count = len(self.loaded)
        status = "BLOCKED" if count > self.limit else "READY"
        changed = status != self.last_status
        self.last_status = status
        return {"loaded_packages": count, "visual_capacity": self.limit, "status": status, "dispatch_allowed": status == "READY", "changed": changed}


class HubState:
    def __init__(self, time_multiplier: float = 60.0) -> None:
        self.time_multiplier = time_multiplier
        self.tracks: dict[str, dict] = {}
        self.last_level = "LOW"

    def zone_for(self, center: list[float], width: int, height: int) -> str:
        x, y = center
        if y < height * 0.38:
            return "INBOUND" if x < width * 0.35 else "QUEUE"
        if y < height * 0.68:
            return "SORTING" if x < width * 0.55 else "STAGING"
        return "LOADING" if x < width * 0.75 else "OUTBOUND"

    def update(self, markers: list[dict], width: int, height: int) -> dict:
        now = time.time()
        for marker in markers:
            track_id = marker["track_id"]
            zone = self.zone_for(marker["center"], width, height)
            current = self.tracks.get(track_id)
            if not current or current["current_zone"] != zone:
                self.tracks[track_id] = {"current_zone": zone, "previous_zone": current["current_zone"] if current else None, "entered_at": now, "marker": marker}
            else:
                current["marker"] = marker
        by_zone: dict[str, int] = {}
        dwell_values = []
        for track in self.tracks.values():
            zone = track["current_zone"]
            by_zone[zone] = by_zone.get(zone, 0) + 1
            dwell_values.append((now - track["entered_at"]) * self.time_multiplier / 60)
        queue = by_zone.get("QUEUE", 0)
        avg_dwell = sum(dwell_values) / len(dwell_values) if dwell_values else 0
        occupancy = min(1.0, len(self.tracks) / 12)
        score = min(100, round(occupancy * 25 + min(queue / 8, 1) * 20 + min(avg_dwell / 10, 1) * 25 + max(0, queue - by_zone.get("OUTBOUND", 0)) * 3))
        level = "CRITICAL" if score >= 75 else "HIGH" if score >= 55 else "MODERATE" if score >= 30 else "LOW"
        changed = level != self.last_level
        self.last_level = level
        return {"zone_counts": by_zone, "queue_length": queue, "average_dwell_min": round(avg_dwell, 1), "occupancy_ratio": round(occupancy, 2), "congestion_score": score, "congestion_level": level, "changed": changed}
