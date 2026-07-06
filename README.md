# LogiSense AI

Green & Resilient Logistics Command Center for the Routix project.

This is a competition-grade prototype that combines delivery risk prediction, SLA risk scoring, green multi-objective routing, carbon estimates, hub congestion intelligence, fleet utilization, maintenance recommendations, a deterministic decision engine, alerts, and a simulated near-real-time SHP-1028 demo flow.

## Architecture

Streamlit frontend -> FastAPI backend -> service layer -> domain modules -> repository helpers -> SQLite plus local data folders.

The frontend never opens SQLite, loads models, or runs optimization directly.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Initialize Database

```bash
python scripts/initialize_database.py
```

## Generate Demo Data

```bash
python scripts/generate_demo_data.py
```

## Train/Register Models

```bash
python scripts/train_delay_model.py
python scripts/train_sla_model.py
python scripts/train_carbon_model.py
python scripts/train_maintenance_model.py
python scripts/train_yolo.py
```

## Start Backend

```bash
uvicorn backend.main:app --reload
```

Open Swagger at http://127.0.0.1:8000/docs.

## Start Frontend

```bash
streamlit run frontend/app.py
```

## Run Tests

```bash
python -m pytest
```

## Demo Workflow

1. Open Command Center and confirm the synthetic environment badge.
2. Open Delivery Risk AI and select `SHP-1028`.
3. Run a loading analysis. Without YOLO weights, Demo Detection Mode is clearly disclosed.
4. Run risk prediction and inspect predicted delay, SLA probability, risk level, and factors.
5. Open Green Route Optimizer, select `SHP-1028`, and run Balanced AI optimization.
6. Open Live Simulation, reset, and advance events: traffic, weather, hub, and GPS.
7. Watch delivery risk, hub risk, route recommendation, and alerts update.
8. Open Analytics & Impact and Reports for calculated impact and exportable JSON.

## Honesty and Limitations

All seeded data is synthetic. Model metrics are generated against prototype synthetic target logic and are not field-validated logistics performance. Route distances use simplified Haversine-derived estimates, and carbon output is an estimate, not certified accounting.

## Customization

- Colors and page styling: `frontend/components/ui.py`
- Risk thresholds and route weights: `config/settings.py`
- Carbon factors: `config/settings.py`
- Synthetic data generation: `scripts/generate_demo_data.py`
- Training formulas: `scripts/model_training_common.py`
- Loading rules: `modules/loading/analyzer.py`
- Decision rules: `modules/decision_engine/engine.py`
- Route optimizer: `modules/routing/optimizer.py`
