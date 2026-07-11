from __future__ import annotations

import threading
import time

from cv_worker.config import config


class CameraManager:
    def __init__(self) -> None:
        self.running = False
        self.status = "OFFLINE"
        self.camera_fps = 0.0
        self.latest_frame = None
        self._thread: threading.Thread | None = None
        self._capture = None

    def start(self) -> None:
        if self.running:
            return
        try:
            import cv2  # type: ignore
        except Exception:
            self.status = "OPENCV_NOT_INSTALLED"
            return
        self._capture = cv2.VideoCapture(config.camera_index)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)
        if not self._capture.isOpened():
            self.status = "CAMERA_UNAVAILABLE"
            return
        self.running = True
        self.status = "ONLINE"
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        frames = 0
        started = time.time()
        while self.running and self._capture is not None:
            ok, frame = self._capture.read()
            if ok:
                self.latest_frame = frame
                frames += 1
                elapsed = time.time() - started
                if elapsed >= 1:
                    self.camera_fps = frames / elapsed
                    frames = 0
                    started = time.time()
            else:
                time.sleep(0.05)

    def stop(self) -> None:
        self.running = False
        if self._capture is not None:
            self._capture.release()
        self._capture = None
        self.status = "OFFLINE"

    def jpeg(self) -> bytes | None:
        if self.latest_frame is None:
            return None
        try:
            import cv2  # type: ignore
            ok, buf = cv2.imencode(".jpg", self.latest_frame)
            return bytes(buf) if ok else None
        except Exception:
            return None
