# LogiSense AI — Implementation Plan

## 1. Build Strategy

The project will be built in risk order, not visual order.

The correct build sequence is:

```text
DATA + DATABASE
        ↓
FASTAPI FOUNDATION
        ↓
MODULE 1 RISK MODELS
        ↓
CARBON BASELINE
        ↓
MODULE 2 ROUTING
        ↓
MODULE 3 HUB / FLEET
        ↓
DECISION ENGINE
        ↓
SIMULATOR
        ↓
STREAMLIT FRONTEND
        ↓
INTEGRATION
        ↓
TESTING
        ↓
POLISH
```

Do not start by building beautiful dashboard pages with fake metrics.

---

## 2. Milestone 1 — Foundation

### Goal

A repository that runs with an empty database.

### Deliverables

- repository structure;
- environment settings;
- FastAPI `/health`;
- SQLite initialization;
- repositories;
- logging;
- tests for database startup.

### Exit criteria

```text
python scripts/initialize_database.py
uvicorn backend.main:app --reload
GET /health → 200
pytest foundation tests → pass
```

---

## 3. Milestone 2 — Demo Data Platform

### Goal

Generate a realistic, repeatable logistics simulation dataset.

### Deliverables

- shipments;
- vehicles;
- hubs;
- traffic;
- weather;
- GPS events;
- hub events;
- routes;
- maintenance history;
- ordered simulation events.

### Exit criteria

- clean database can be seeded;
- SHP-1028 exists;
- critical congestion scenario exists;
- route candidate data can be created;
- all data labeled synthetic.

---

## 4. Milestone 3 — Delivery Risk AI

### Goal

Predict delay and SLA risk through backend APIs.

### Build order

1. feature engineering;
2. synthetic target generation;
3. baselines;
4. candidate model training;
5. evaluation;
6. selected model persistence;
7. inference wrappers;
8. service;
9. API;
10. tests.

### Exit criteria

```text
POST /api/risk/predict/SHP-1028
```

returns:

- predicted delay;
- SLA probability;
- risk level;
- model source;
- main factors.

High/Critical risk can generate an alert.

---

## 5. Milestone 4 — Loading Vision

### Goal

Add loading context without blocking the main logistics pipeline.

### Build order

1. image validation;
2. YOLO wrapper;
3. demo fallback;
4. compliance scoring;
5. annotation;
6. service;
7. API;
8. training/evaluation scripts.

### Exit criteria

- real model runs when file exists;
- Demo Detection Mode runs when absent;
- no fake YOLO metrics;
- result can feed delivery risk feature context.

---

## 6. Milestone 5 — Carbon Engine

### Goal

Calculate transparent carbon estimates.

### Build order

1. deterministic calculator;
2. tests;
3. carbon API;
4. optional synthetic regression model;
5. metadata and disclosure.

### Exit criteria

Every route candidate can return:

- estimated fuel;
- estimated CO₂;
- carbon calculation source.

---

## 7. Milestone 6 — Green Route Optimizer

### Goal

Generate and compare multi-objective route candidates.

### Build order

1. route schemas;
2. capacity validation;
3. Haversine;
4. matrices;
5. current route;
6. OR-Tools;
7. route metrics;
8. objective normalization;
9. GA;
10. presets;
11. recommendation logic;
12. API;
13. tests.

### Exit criteria

One API request returns:

- current route;
- OR-Tools;
- Fastest;
- Greenest;
- SLA Priority;
- Balanced AI.

Each candidate contains:

- distance;
- time;
- fuel;
- CO₂;
- SLA risk;
- objective score.

---

## 8. Milestone 7 — Hub and Fleet Resilience

### Goal

Detect hub bottlenecks and show network/fleet vulnerability.

### Build order

1. hub features;
2. congestion score;
3. bottleneck detector;
4. trend aggregation;
5. heatmap data;
6. optional anomaly model;
7. fleet utilization;
8. maintenance rules;
9. APIs;
10. tests.

### Exit criteria

A hub analysis returns:

- congestion score;
- risk level;
- queue growth;
- dwell excess;
- likely bottleneck;
- impact estimate.

Fleet analysis returns:

- utilization;
- high-use vehicles;
- underused vehicles.

---

## 9. Milestone 8 — Decision Engine

### Goal

Convert predictions into recommendations.

### Build order

1. decision schema;
2. SLA rules;
3. hub rules;
4. route recommendation rule;
5. maintenance rule;
6. alert service;
7. deduplication;
8. acknowledgement;
9. tests.

### Exit criteria

Computed conditions create deterministic, explainable alerts.

---

## 10. Milestone 9 — Live Simulation

### Goal

Demonstrate near-real-time decision changes.

### Build order

1. event schema;
2. event loader;
3. simulation state;
4. reset;
5. next event;
6. state mutation;
7. affected-entity resolver;
8. module rescoring;
9. decision engine;
10. route reoptimization;
11. API.

### Exit criteria

The SHP-1028 scenario can be advanced event by event and visibly changes:

- delay;
- SLA risk;
- hub risk;
- route recommendation;
- alerts.

---

## 11. Milestone 10 — Streamlit Frontend

Build pages only after backend workflows are stable.

Order:

1. API client;
2. shared components;
3. Command Center;
4. Delivery Risk;
5. Route Optimizer;
6. Network Resilience;
7. Live Simulation;
8. Analytics;
9. Data & Models;
10. Reports.

### Exit criteria

No page directly imports:

- SQLite connection;
- YOLO;
- sklearn model;
- OR-Tools.

---

## 12. Milestone 11 — Integration Testing

Test:

```text
event
→ state update
→ risk prediction
→ hub analysis
→ decision
→ route optimization
→ alert
→ analytics
→ frontend display
```

The full chain must be exercised with API integration tests and manual demo verification.

---

## 13. Milestone 12 — Competition Polish

Finalize:

- honest metrics;
- architecture diagram;
- workflow diagram;
- model registry;
- business impact assumptions;
- demo script;
- screenshots;
- executive summary;
- judge Q&A.

---

## 14. Suggested 8-Week Schedule

| Week | Focus |
|---|---|
| 1 | Foundation, database, demo data |
| 2 | Delay + SLA models |
| 3 | Loading vision + carbon engine |
| 4 | Route optimization |
| 5 | Hub + fleet resilience |
| 6 | Decision engine + simulator |
| 7 | Streamlit + integration |
| 8 | Testing, metrics, presentation |

For a shorter timeline, loading vision and maintenance ML may remain demo/fallback capabilities while delay, SLA, routing, carbon, and hub congestion receive priority.

---

## 15. Priority Order if Time Runs Out

### Must have

1. Delay Prediction
2. SLA Risk
3. Multi-objective Route Optimizer
4. Carbon Analytics
5. Hub Congestion / Bottleneck
6. Decision Engine + Alerts
7. Dashboard
8. Simulation workflow

### Strong supporting features

9. Fleet Utilization
10. YOLO Loading Risk

### Optional / last priority

11. Maintenance ML classifier/regressor
12. RL/PPO
13. Real external APIs
14. PDF export

This priority order preserves competition alignment.
