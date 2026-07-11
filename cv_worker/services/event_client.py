from __future__ import annotations

import json
import queue
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from typing import Any

from cv_worker.config import config


class EventClient:
    def __init__(self, backend_url: str | None = None, max_queue: int = 100) -> None:
        self.backend_url = (backend_url or config.backend_url).rstrip("/")
        self.queue: queue.Queue[dict] = queue.Queue(maxsize=max_queue)
        self.history: deque[dict] = deque(maxlen=25)
        self.failed_event_count = 0
        self.delivered_event_count = 0
        self.last_success_at: str | None = None
        self.last_result: dict[str, Any] | None = None
        self.delivery_status = "IDLE"
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def send(self, event: dict) -> dict:
        try:
            self.queue.put_nowait(event)
        except queue.Full:
            self.failed_event_count += 1
            self.delivery_status = "FAILED"
            self.last_result = {"accepted": False, "delivery_status": "FAILED", "error": "local event queue full", "event_id": event.get("event_id")}
            self.history.appendleft(self.last_result)
            return self.last_result
        self.delivery_status = "QUEUED"
        self.last_result = {"accepted": False, "delivery_status": "QUEUED", "event_id": event.get("event_id"), "queue_size": self.queue.qsize()}
        self.history.appendleft(self.last_result)
        return self.last_result

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                event = self.queue.get(timeout=0.25)
            except queue.Empty:
                continue
            result = self._deliver_with_retry(event)
            self.last_result = result
            self.history.appendleft(result)
            self.queue.task_done()

    def _deliver_with_retry(self, event: dict) -> dict:
        delay = 0.4
        for attempt in range(1, 4):
            result = self._deliver_once(event, attempt)
            if result.get("accepted"):
                self.delivered_event_count += 1
                self.delivery_status = "DELIVERED"
                return result
            time.sleep(delay)
            delay *= 2
        self.failed_event_count += 1
        self.delivery_status = "FAILED"
        return {**result, "delivery_status": "FAILED"}

    def _deliver_once(self, event: dict, attempt: int) -> dict:
        payload = json.dumps(event).encode("utf-8")
        request = urllib.request.Request(
            f"{self.backend_url}/api/cv/events",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))
                self.last_success_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                return {**data, "delivery_status": "DELIVERED", "attempt": attempt}
        except Exception as exc:
            return {"accepted": False, "delivery_status": "QUEUED", "attempt": attempt, "event_id": event.get("event_id"), "error": str(exc)}

    def flush(self, timeout: float = 5.0) -> list[dict]:
        deadline = time.time() + timeout
        while not self.queue.empty() and time.time() < deadline:
            time.sleep(0.05)
        return list(self.history)

    def stop(self) -> None:
        self._stop.set()
