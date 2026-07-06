# LogiSense AI — Product and System Workflow

## 1. Simplest Three-Module Workflow

```text
MODULE 1
DELIVERY & LOADING RISK AI
"Will this shipment have a problem?"
        ↓
MODULE 2
GREEN ROUTE OPTIMIZER
"What route should we use?"
        ↓
MODULE 3
NETWORK & FLEET RESILIENCE AI
"Where will the network have a problem?"
        ↓
DECISION ENGINE
"What should the operator do?"
        ↓
COMMAND CENTER
"Show the risk, recommendation, carbon impact, and alert."
```

---

## 2. Complete Data Workflow

```text
TRAFFIC
WEATHER
GPS
SHIPMENT / ERP-LIKE DATA
TMS / ROUTE DATA
HUB DATA
CAMERA / LOADING DATA
VEHICLE HISTORY
        ↓
DATA INGESTION
Batch + Simulated Stream
        ↓
STORAGE
SQLite + Local Data Lake
        ↓
CURRENT OPERATIONAL SNAPSHOT
        ↓
┌─────────────────────────────────────────────────┐
│ MODULE 1 — DELIVERY & LOADING RISK AI           │
│                                                 │
│ YOLO Loading Risk                               │
│ Delay Prediction                                │
│ SLA Risk Scoring                                │
└───────────────────────┬─────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│ MODULE 2 — GREEN MULTI-OBJECTIVE ROUTING        │
│                                                 │
│ Time + Fuel + CO₂ + SLA Risk                    │
│ OR-Tools Baseline                               │
│ Genetic Algorithm                               │
│ Fastest / Greenest / Balanced Route             │
└───────────────────────┬─────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│ MODULE 3 — NETWORK & FLEET RESILIENCE           │
│                                                 │
│ Hub Congestion                                  │
│ Bottleneck Detection                            │
│ Fleet Utilization                               │
│ Preventive Maintenance                          │
└───────────────────────┬─────────────────────────┘
                        ↓
DECISION ENGINE
                        ↓
ALERTS
ROUTE RECOMMENDATION
CARBON ANALYTICS
RISK HEATMAP
FLEET INSIGHTS
                        ↓
LOGISTICS COMMAND CENTER
```

---

## 3. Module 1 Workflow

```text
SELECT SHIPMENT
        ↓
LOAD SHIPMENT DATA
        ↓
LOAD LATEST TRAFFIC
        ↓
LOAD LATEST WEATHER
        ↓
LOAD LATEST GPS STATE
        ↓
LOAD HUB DWELL / CONGESTION
        ↓
OPTIONAL LOADING IMAGE
        ↓
YOLO LOADING ANALYSIS
        ↓
FEATURE ENGINEERING
        ↓
DELAY REGRESSION
        ↓
PREDICTED DELAY MINUTES
        ↓
SLA FEATURE BUILD
        ↓
SLA CLASSIFICATION
        ↓
SLA RISK PROBABILITY
        ↓
LOW / MEDIUM / HIGH / CRITICAL
        ↓
DECISION ENGINE
        ↓
ALERT IF REQUIRED
```

---

## 4. Module 2 Workflow

```text
SELECT SHIPMENT / DELIVERY BATCH
        ↓
SELECT VEHICLE
        ↓
CHECK WEIGHT CAPACITY
        ↓
CHECK VOLUME CAPACITY
        ↓
LOAD TRAFFIC / WEATHER / SLA CONTEXT
        ↓
BUILD ROUTE MATRICES
        ↓
CALCULATE CURRENT ROUTE
        ↓
RUN OR-TOOLS BASELINE
        ↓
RUN GENETIC ALGORITHM WITH PRESETS
        ↓
FASTEST ROUTE
GREENEST ROUTE
SLA PRIORITY ROUTE
BALANCED AI ROUTE
        ↓
CALCULATE EACH ROUTE:
TIME
FUEL
CO₂
SLA RISK
        ↓
DECISION ENGINE
        ↓
HIGHLIGHT RECOMMENDED ROUTE
        ↓
SAVE RECOMMENDATION
```

---

## 5. Module 3 Workflow

```text
HUB EVENTS
        ↓
ARRIVALS / DEPARTURES / QUEUE / DWELL / PROCESS TIMES
        ↓
HUB FEATURE ENGINEERING
        ↓
CONGESTION SCORE
        ↓
BOTTLENECK DETECTION
        ↓
HUB RISK LEVEL
        ↓
DECISION ENGINE
        ↓
HUB ALERT

VEHICLE / ROUTE / LOAD / SERVICE HISTORY
        ↓
FLEET UTILIZATION
        ↓
HIGH-USE / UNDERUSED VEHICLE INSIGHT
        ↓
MAINTENANCE FEATURE ENGINEERING
        ↓
OPERATIONAL HEALTH SCORE
        ↓
CHECK-UP RECOMMENDATION
        ↓
FLEET ALERT IF REQUIRED
```

---

## 6. Near-Real-Time Simulation Workflow

```text
SIMULATION START
        ↓
INITIAL STATE
Traffic = Moderate
Weather = Clear
Hub B = Normal
SLA Risk = Medium
        ↓
NEXT EVENT
        ↓
TRAFFIC_UPDATE
Traffic = Severe
        ↓
MODULE 1 RESCORES DELAY / SLA
        ↓
SLA Risk increases
        ↓
DECISION ENGINE checks threshold
        ↓
NEXT EVENT
        ↓
WEATHER_UPDATE
Heavy Rain
        ↓
MODULE 1 RESCORES
        ↓
NEXT EVENT
        ↓
HUB_UPDATE
Dwell +42 min
Queue Growing
        ↓
MODULE 3 detects High Hub Risk
        ↓
MODULE 1 receives hub risk context
        ↓
SLA Risk becomes Critical
        ↓
CRITICAL ALERT
        ↓
MODULE 2 REOPTIMIZES
        ↓
Balanced AI Route becomes better policy choice
        ↓
ROUTE RECOMMENDATION ALERT
        ↓
COMMAND CENTER UPDATES
```

---

## 7. Frontend Workflow

```text
STREAMLIT PAGE
        ↓
USER ACTION
        ↓
API CLIENT
        ↓
FASTAPI ENDPOINT
        ↓
SERVICE
        ↓
DOMAIN / ML / OPTIMIZATION
        ↓
REPOSITORY
        ↓
SQLITE
        ↓
SERVICE RESPONSE
        ↓
FASTAPI JSON
        ↓
API CLIENT
        ↓
STREAMLIT VISUALIZATION
```

---

## 8. End-to-End Demo Workflow

```text
1. Open Command Center
2. See synthetic demo environment
3. Open SHP-1028
4. View initial Medium SLA risk
5. Run/inspect loading analysis
6. Open Live Simulation
7. Advance Traffic Update
8. Delay prediction increases
9. Advance Heavy Rain Update
10. SLA risk increases
11. Advance Hub Congestion Update
12. Hub B becomes High/Critical
13. SLA risk becomes High/Critical
14. Decision engine creates alert
15. Route reoptimization runs
16. Compare Current / Fastest / Greenest / Balanced
17. View CO₂ and SLA trade-off
18. Accept/save route recommendation
19. Open Network Resilience
20. Inspect Hub B bottleneck
21. Inspect fleet utilization
22. Inspect vehicle check-up recommendation
23. Open Analytics & Impact
24. View computed route, fuel, carbon, and SLA impact
25. Export executive summary
```
