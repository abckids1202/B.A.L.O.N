from __future__ import annotations

import asyncio

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from cv_worker.runtime import runtime


app = FastAPI(title="B.A.L.O.N Local CV Worker", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return runtime.status()


@app.get("/status")
def status():
    return runtime.status()


@app.post("/control/start")
def start():
    runtime.camera.start()
    return runtime.status()


@app.post("/control/stop")
def stop():
    runtime.camera.stop()
    return runtime.status()


@app.post("/control/reset")
def reset():
    runtime.mode = "IDLE"
    return runtime.status()


@app.post("/control/mode")
def mode(payload: dict = Body(...)):
    runtime.mode = str(payload.get("mode") or "IDLE").upper()
    return runtime.status()


@app.get("/stream")
async def stream():
    async def frames():
        boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
        while True:
            jpeg = runtime.camera.jpeg()
            if jpeg:
                yield boundary + jpeg + b"\r\n"
            await asyncio.sleep(0.05)
    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")
