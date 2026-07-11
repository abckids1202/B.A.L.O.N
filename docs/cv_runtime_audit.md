# CV Runtime Audit

Previous state: `python -m cv_worker.main` only started the FastAPI worker API with Uvicorn. It did not open a local camera window, so the physical CV demo could not prove raw webcam capture. If the user did not keep that terminal running, `http://127.0.0.1:8765/docs` would not open.

Repair implemented:

- `cv_worker.main` now starts the worker API on `127.0.0.1:8765` in a background thread.
- The foreground process opens an OpenCV desktop window.
- The camera starts even when model weights are missing.
- Key controls switch the four operational modes.
- Pressing `E` sends one normalized material CV event to `POST /api/cv/events`.
- Model status remains honest: datasets are present, weights are missing until training/export.

Current model asset status:

- Package dataset: `Package and label detection.v4i.yolov11`
- Package weights: not found
- Damage dataset: `Parcel Damage Detection.v2-roboflow-instant-2--eval-.yolov11`
- Damage weights: not found
