from __future__ import annotations

import time

from cv_worker.runtime import runtime


MODE_KEYS = {
    ord("1"): "PACKAGE_QUALITY",
    ord("2"): "DISPATCH_VALIDATION",
    ord("3"): "LOADING_COMPLIANCE",
    ord("4"): "HUB_VISION",
}


def _put_lines(cv2, frame, lines: list[str]) -> None:
    x, y = 16, 28
    for line in lines:
        cv2.putText(frame, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1, cv2.LINE_AA)
        y += 24


def _annotate(cv2, frame):
    status = runtime.status()
    mode = status["active_mode"]
    h, w = frame.shape[:2]
    color = (52, 211, 153) if runtime.camera.status == "ONLINE" else (0, 0, 255)
    cv2.rectangle(frame, (8, 8), (min(w - 8, 760), 188), (15, 23, 42), -1)
    lines = [
        "B.A.L.O.N LOCAL CV DESKTOP - raw camera proof",
        f"Mode: {mode} | Camera: {status['camera_status']} | Backend: {'ON' if status['backend_enabled'] else 'OFF'} | Events: {status['events_emitted']}",
        f"FPS: {status['camera_fps']:.1f} | Package model: {status['package_model_status']} | Damage model: {status['damage_model_status']} | QR: {status['qr_status']}",
        "Keys: 1 Damage  2 Wrong Loading  3 Loading  4 Hub  E Emit event  B Backend  S Start  P Pause  R Reset  Q Quit",
        f"Last backend: {str(status['last_backend_result'])[:100] if status['last_backend_result'] else 'none'}",
    ]
    _put_lines(cv2, frame, lines)
    if mode == "PACKAGE_QUALITY":
        cv2.rectangle(frame, (int(w * .28), int(h * .28)), (int(w * .72), int(h * .72)), color, 2)
        cv2.putText(frame, "package ROI / damage proof", (int(w * .28), int(h * .28) - 8), cv2.FONT_HERSHEY_SIMPLEX, .65, color, 2)
    elif mode == "DISPATCH_VALIDATION":
        cv2.rectangle(frame, (int(w * .38), int(h * .28)), (int(w * .62), int(h * .58)), (59, 130, 246), 2)
        cv2.putText(frame, "QR / label zone", (int(w * .38), int(h * .28) - 8), cv2.FONT_HERSHEY_SIMPLEX, .65, (59, 130, 246), 2)
    elif mode == "LOADING_COMPLIANCE":
        cv2.line(frame, (int(w * .45), int(h * .18)), (int(w * .45), int(h * .86)), (245, 158, 11), 3)
        cv2.putText(frame, "entry line / count proof", (int(w * .45) + 8, int(h * .2)), cv2.FONT_HERSHEY_SIMPLEX, .65, (245, 158, 11), 2)
    else:
        for i, label in enumerate(["INBOUND", "QUEUE", "SORTING", "LOADING"]):
            x1 = int((.08 + (i % 2) * .43) * w)
            y1 = int((.28 + (i // 2) * .32) * h)
            x2 = int(x1 + .32 * w)
            y2 = int(y1 + .22 * h)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (124, 58, 237), 2)
            cv2.putText(frame, label, (x1 + 8, y1 + 26), cv2.FONT_HERSHEY_SIMPLEX, .65, (124, 58, 237), 2)
    return frame


def run_desktop(camera_index: int = 0, source_video: str | None = None) -> None:
    import cv2  # type: ignore

    runtime.camera.configure(camera_index=camera_index, source_video=source_video)
    runtime.camera.start()
    window = "B.A.L.O.N Local CV Demo"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, 1120, 720)
    last = time.perf_counter()
    try:
        while True:
            frame = runtime.camera.frame()
            if frame is None:
                frame = 255 * __import__("numpy").ones((480, 800, 3), dtype="uint8")
                cv2.putText(frame, f"Camera unavailable: {runtime.camera.status} {runtime.camera.error}", (24, 220), cv2.FONT_HERSHEY_SIMPLEX, .75, (0, 0, 255), 2)
            now = time.perf_counter()
            runtime.inference_latency_ms = (now - last) * 1000
            last = now
            frame = _annotate(cv2, frame)
            cv2.imshow(window, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in MODE_KEYS:
                runtime.mode = MODE_KEYS[key]
            elif key in {ord("q"), 27}:
                break
            elif key == ord("s"):
                runtime.camera.start()
            elif key == ord("p"):
                runtime.camera.stop()
            elif key == ord("r"):
                runtime.last_backend_result = None
                runtime.last_event = None
            elif key == ord("b"):
                runtime.backend_enabled = not runtime.backend_enabled
            elif key == ord("e"):
                runtime.emit_material_event()
    finally:
        runtime.camera.stop()
        cv2.destroyAllWindows()
