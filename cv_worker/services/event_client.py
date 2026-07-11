from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections import deque

from cv_worker.config import config


class EventClient:
    def __init__(self, backend_url: str | None = None) -> None:
        self.backend_url = (backend_url or config.backend_url).rstrip("/")
        self.queue: deque[dict] = deque(maxlen=100)
        self.failed_event_count = 0
        self.last_success_at: str | None = None

    def send(self, event: dict) -> dict:
        payload = json.dumps(event).encode("utf-8")
        request = urllib.request.Request(f"{self.backend_url}/api/cv/events", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                self.last_success_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            self.failed_event_count += 1
            self.queue.append(event)
            return {"accepted": False, "queued": True, "error": str(exc)}

    def flush(self) -> list[dict]:
        results = []
        for _ in range(len(self.queue)):
            results.append(self.send(self.queue.popleft()))
        return results
