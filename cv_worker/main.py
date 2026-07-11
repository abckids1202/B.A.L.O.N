from __future__ import annotations

import argparse
import json
import socket
import threading
import urllib.error
import urllib.request

import uvicorn

from cv_worker.config import config
from cv_worker.desktop_app import run_desktop
from cv_worker.model_registry import print_startup_diagnostics
from cv_worker.runtime import runtime


def _worker_health(port: int) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1.5) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


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
    parser.add_argument("--desktop-only", action="store_true", help="Run a camera window without owning port 8765. Use only for diagnostics.")
    args = parser.parse_args()

    runtime.mode = args.mode
    runtime.backend_enabled = not args.no_backend
    runtime.set_backend_url(args.backend_url)

    existing = _worker_health(config.worker_port)
    api_thread = None
    if existing and not args.desktop_only:
        print(f"Another healthy CV worker already owns http://127.0.0.1:{config.worker_port}.")
        print("This launch will exit to avoid a camera process disconnected from the API/web frontend.")
        print("Use --desktop-only only for camera diagnostics, or close the existing worker first.")
        return
    if _port_open(config.worker_port) and not args.desktop_only:
        print(f"Port {config.worker_port} is occupied but /health did not respond as a B.A.L.O.N worker.")
        print("Close the process using the port, change CV_WORKER_PORT, or launch with --desktop-only for diagnostics.")
        return
    if not args.desktop_only:
        api_thread = threading.Thread(target=_run_api, daemon=True)
        api_thread.start()
        print(f"Local CV worker API: http://127.0.0.1:{config.worker_port}/docs")
    else:
        print("Desktop-only diagnostic mode: no worker API is started, and the web frontend will not read this runtime.")
    print_startup_diagnostics()
    print("Desktop controls: 1/2/3/4 switch mode, A analyzes damage, E queues one backend event, F1/F2 or C/W switch context, B toggles backend, Q quits.")
    if args.api_only:
        if api_thread:
            api_thread.join()
        return
    run_desktop(camera_index=args.camera_index, source_video=args.source_video if args.source == "video" else None)


if __name__ == "__main__":
    main()
