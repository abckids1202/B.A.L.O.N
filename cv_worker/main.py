from __future__ import annotations

import argparse
import threading

import uvicorn

from cv_worker.config import config
from cv_worker.desktop_app import run_desktop
from cv_worker.runtime import runtime


def _run_api() -> None:
    uvicorn.run("cv_worker.api:app", host="127.0.0.1", port=config.worker_port, reload=False, log_level="warning")


def main() -> None:
    parser = argparse.ArgumentParser(description="B.A.L.O.N local CV desktop demo")
    parser.add_argument("--mode", default="PACKAGE_QUALITY", choices=["PACKAGE_QUALITY", "DISPATCH_VALIDATION", "LOADING_COMPLIANCE", "HUB_VISION", "IDLE"])
    parser.add_argument("--camera-index", type=int, default=config.camera_index)
    parser.add_argument("--source", default="webcam", choices=["webcam", "video"])
    parser.add_argument("--source-video")
    parser.add_argument("--backend-url", default=config.backend_url)
    parser.add_argument("--confidence", type=float, default=config.confidence_threshold)
    parser.add_argument("--device", default=config.device)
    parser.add_argument("--no-backend", action="store_true")
    parser.add_argument("--api-only", action="store_true")
    args = parser.parse_args()

    runtime.mode = args.mode
    runtime.backend_enabled = not args.no_backend
    runtime.set_backend_url(args.backend_url)

    api_thread = threading.Thread(target=_run_api, daemon=True)
    api_thread.start()
    print("Local CV worker API: http://127.0.0.1:8765/docs")
    print("Desktop controls: 1/2/3/4 switch mode, E emits one backend event, B toggles backend, Q quits.")
    if args.api_only:
        api_thread.join()
        return
    run_desktop(camera_index=args.camera_index, source_video=args.source_video if args.source == "video" else None)


if __name__ == "__main__":
    main()
