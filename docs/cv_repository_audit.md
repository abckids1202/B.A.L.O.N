# CV Repository Audit

- Package dataset: `Package and label detection.v4i.yolov11/data.yaml`
- Package classes: `label`, `package`
- Package weights: none discovered (`.pt`/`.onnx` not present)
- Damage dataset: `Parcel Damage Detection.v2-roboflow-instant-2--eval-.yolov11/data.yaml`
- Damage classes: `crushed`, `dirt`, `puncture`, `tear`, `torn`, `wet`
- Damage weights: none discovered (`.pt`/`.onnx` not present)
- Frontend: React/Vite single app in `frontend/src/main.jsx`
- Backend: FastAPI routes in `backend/api/routes.py`, operational logic in `backend/services/core.py`
- Integration plan: local `cv_worker` emits normalized events to `/api/cv/events`; backend updates existing signals, twins, forecasts, and analytics.
