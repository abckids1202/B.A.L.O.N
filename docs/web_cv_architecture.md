# Web CV Assessor Mode

B.A.L.O.N now supports two computer-vision runtimes.

Local Pro Mode keeps the existing OpenCV desktop worker:

```text
python -m cv_worker.main --camera-index 0
```

Web Assessor Mode runs from the deployed React app:

```text
Vercel React live browser camera
-> Render FastAPI /api/web-cv
-> shared model adapters and CV state machines
-> existing /api/cv/events ingestion
-> SSE updates on the Visual Intelligence pages
```

Vercel never runs Python, OpenCV, or model inference. The browser captures deliberate JPEG snapshots from the live camera and sends them to Render only when the assessor presses a module action. Render validates the image, runs the module logic, emits a normalized CV event, and returns Detection -> Analysis -> Decision -> Impact data.

## Pages

- Package Quality: package YOLO plus damage classifier.
- Dispatch Validation: browser camera frame plus browser QR decoding when available, with backend OpenCV QR fallback and authoritative assignment validation.
- Loading Compliance: one frozen snapshot, ROI filtering, overlap dedupe, and capacity decision.
- Hub Vision: one-package journey timing across Receiving, Processing, and Dispatch.

## API

- `GET /api/web-cv/health`
- `GET /api/web-cv/models/status`
- `POST /api/web-cv/sessions`
- `GET /api/web-cv/sessions/{session_id}`
- `POST /api/web-cv/sessions/{session_id}/reset`
- `DELETE /api/web-cv/sessions/{session_id}`
- `POST /api/web-cv/package-quality/analyze`
- `POST /api/web-cv/dispatch/scan`
- `POST /api/web-cv/loading/snapshot`
- `POST /api/web-cv/hub/start`
- `POST /api/web-cv/hub/frame`
- `POST /api/web-cv/hub/stop`
- `POST /api/web-cv/hub/reset`

Image endpoints accept `multipart/form-data` with `session_id` and `file`.
