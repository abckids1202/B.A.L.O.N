# Web CV Deployment

## Render Backend

Use the existing FastAPI backend service.

Start command:

```text
python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Recommended environment:

```env
CV_WEB_ENABLED=true
CV_PACKAGE_MODEL_PATH=models/cv/package_detector/v1/best.pt
CV_DAMAGE_MODEL_PATH=models/cv/damage_detector/v1/damage_detector.pth
CV_DEVICE=cpu
CV_CONFIDENCE_THRESHOLD=0.75
CV_WEB_MAX_CONCURRENT_INFERENCE=1
CV_WEB_INFERENCE_TIMEOUT_SECONDS=30
CV_MAX_UPLOAD_MB=6
CV_MAX_IMAGE_DIMENSION=1600
CV_WEB_SESSION_TTL_MINUTES=30
CV_LOADING_MAX_PACKAGES=5
CV_HUB_DEMO_ZONE_1_SECONDS=10
CV_HUB_DEMO_ZONE_2_SECONDS=10
CV_HUB_DEMO_ZONE_3_SECONDS=4
CV_HUB_REAL_ZONE_1_HOURS=72.48
CV_HUB_REAL_ZONE_2_HOURS=72.00
CV_HUB_REAL_ZONE_3_HOURS=3.50
LOGISENSE_CORS_ORIGINS=http://localhost:5173,https://YOUR-VERCEL-DOMAIN.vercel.app
```

Install the normal backend requirements plus CV runtime dependencies from `requirements-cv.txt`.

## Vercel Frontend

Root directory:

```text
frontend
```

Build command:

```text
npm run build
```

Output directory:

```text
dist
```

Environment:

```env
VITE_API_BASE=https://YOUR-RENDER-SERVICE.onrender.com
VITE_CV_WEB_ENABLED=true
VITE_CV_DEMO_ASSETS_ENABLED=true
VITE_CV_LOCAL_WORKER_URL=http://127.0.0.1:8765
```

Camera access requires HTTPS. Vercel production URLs satisfy this.
