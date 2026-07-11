from __future__ import annotations

import threading
import time
from pathlib import Path

from cv_worker.config import config


class CameraManager:
    def __init__(self) -> None:
        self.running = False
        self.status = "OFFLINE"
        self.error = ""
        self.source_type = "WEBCAM"
        self.camera_index = config.camera_index
        self.source_video: str | None = None
        self.camera_fps = 0.0
        self.latest_frame = None
        self.frame_width = 0
        self.frame_height = 0
        self.tested_indexes: list[int] = []
        self._thread: threading.Thread | None = None
        self._capture = None

    def configure(self, camera_index: int | None = None, source_video: str | None = None) -> None:
        if camera_index is not None:
            self.camera_index = camera_index
        self.source_video = source_video
        self.source_type = "VIDEO_FILE" if source_video else "WEBCAM"

    def start(self) -> None:
        if self.running:
            return
        try:
            import cv2  # type: ignore
        except Exception as exc:
            self.status = "OPENCV_NOT_INSTALLED"
            self.error = str(exc)
            return

        capture = None
        self.tested_indexes = []
        if self.source_video:
            if not Path(self.source_video).exists():
                self.status = "VIDEO_NOT_FOUND"
                self.error = self.source_video
                return
            capture = cv2.VideoCapture(self.source_video)
        else:
            for idx in [self.camera_index, 0, 1, 2, 3, 4, 5]:
                if idx in self.tested_indexes:
                    continue
                self.tested_indexes.append(idx)
                capture = cv2.VideoCapture(idx)
                if not capture.isOpened():
                    capture.release()
                    capture = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if capture.isOpened():
                    break
                capture.release()
                capture = None

        if capture is None or not capture.isOpened():
            self.status = "CAMERA_UNAVAILABLE"
            self.error = f"Tested indexes: {self.tested_indexes}"
            return

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)
        ok, frame = capture.read()
        if not ok:
            self.status = "FRAME_READ_FAILED"
            self.error = "Camera opened but first frame could not be read."
            capture.release()
            return
        self.latest_frame = frame
        self.frame_height, self.frame_width = frame.shape[:2]
        self._capture = capture
        self.running = True
        self.status = "ONLINE"
        self.error = ""
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        frames = 0
        started = time.time()
        while self.running and self._capture is not None:
            ok, frame = self._capture.read()
            if not ok and self.source_video:
                self._capture.set(1, 0)
                ok, frame = self._capture.read()
            if ok:
                self.latest_frame = frame
                self.frame_height, self.frame_width = frame.shape[:2]
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

    def reset(self) -> None:
        self.stop()
        self.latest_frame = None
        self.camera_fps = 0.0
        self.error = ""

    def frame(self):
        return None if self.latest_frame is None else self.latest_frame.copy()

    def jpeg(self) -> bytes | None:
        frame = self.frame()
        if frame is None:
            return None
        try:
            import cv2  # type: ignore
            ok, buf = cv2.imencode(".jpg", frame)
            return bytes(buf) if ok else None
        except Exception:
            return None
