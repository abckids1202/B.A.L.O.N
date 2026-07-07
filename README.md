# B.A.L.O.N Logistics Command Center

React frontend plus FastAPI backend for the Routix/LogiSense logistics AI prototype.

## Deployment Shape

- Render: FastAPI backend
- Vercel: React frontend

The frontend calls the backend through `VITE_API_BASE`.

## Local Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/generate_demo_data.py
python scripts/train_delay_model.py
python scripts/train_sla_model.py
python scripts/train_carbon_model.py
python scripts/train_maintenance_model.py
python scripts/train_yolo.py
python -m uvicorn backend.main:app --reload
```

Backend docs:

```text
http://127.0.0.1:8000/docs
```

## Local Frontend

```bash
npm install
npm run dev
```

Frontend:

```text
http://127.0.0.1:5173
```

## Render Backend

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python scripts/generate_demo_data.py && python scripts/train_delay_model.py && python scripts/train_sla_model.py && python scripts/train_carbon_model.py && python scripts/train_maintenance_model.py && python scripts/train_yolo.py && uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Environment variables:

```env
LOGISENSE_TIMEZONE=Asia/Jakarta
LOGISENSE_RANDOM_SEED=42
LOGISENSE_DB_PATH=data/logisense.db
```

## Vercel Frontend

Framework preset:

```text
Vite
```

Root directory:

```text
./
```

Install command:

```bash
npm install
```

Build command:

```bash
npm run build
```

Output directory:

```text
frontend/dist
```

Environment variable:

```env
VITE_API_BASE=https://your-render-backend.onrender.com
```

## Tests

```bash
python -m pytest
npm run build
```

## Demo Flow

1. Deploy/start the backend.
2. Deploy/start the React frontend.
3. Open Command Center.
4. Run `SHP-1028` on Delivery Risk.
5. Optimize routes.
6. Advance Live Simulation events.
7. Review Network Resilience, Analytics, Models, and Reports.

All demo data is synthetic and all prototype metrics are labeled as synthetic-target metrics.
