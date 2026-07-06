# Product Requirements Document (PRD)

**Project:** LogiSense AI — Green & Resilient Logistics Command Center  
**Version:** 2.0 — Pre-Build Planning Baseline  
**Status:** Approved planning baseline; implementation has not started  
**Primary context:** AI Open Innovation Challenge 2026 — Blibli logistics case  
**Prototype type:** Competition-grade AI logistics intelligence platform

---

## 1. Executive Product Definition

LogiSense AI is an integrated logistics intelligence platform that combines predictive delivery risk, multi-objective green routing, loading visibility, hub congestion analysis, and fleet resilience into one near-real-time command center.

The product is intentionally organized into **three major modules**:

1. **Delivery & Loading Risk AI**
2. **Green Multi-Objective Route Optimizer**
3. **Network & Fleet Resilience AI**

The three modules share a common data pipeline and decision engine.

The product must demonstrate this high-level operational chain:

```text
TRAFFIC + WEATHER + GPS + SHIPMENT + HUB + CAMERA + VEHICLE HISTORY
                                  ↓
                         DATA INGESTION
                                  ↓
                    HISTORICAL + LIVE-LIKE DATA
                                  ↓
        ┌─────────────────┬──────────────────┬─────────────────┐
        │ MODULE 1        │ MODULE 2         │ MODULE 3        │
        │ Delivery Risk   │ Green Routing    │ Network/Fleet   │
        └─────────────────┴──────────────────┴─────────────────┘
                                  ↓
                         DECISION ENGINE
                                  ↓
          ALERTS + ROUTE RECOMMENDATIONS + CARBON ANALYTICS
                                  ↓
                  LOGISTICS COMMAND CENTER
```

The platform is a **prototype and simulation-oriented decision-support system**, not a production TMS, ERP, or safety-certified logistics platform.

---

## 2. Product Goal

The product goal is to help logistics operators answer three practical questions:

### Module 1
> Is the shipment operationally safe, and is it likely to be delayed or breach SLA?

### Module 2
> Which route best balances time, fuel, carbon emissions, and SLA risk?

### Module 3
> Where is the logistics network becoming vulnerable, and which hubs or vehicles may create future operational disruption?

The final application should make complex logistics signals understandable through measurable predictions, transparent recommendations, alerts, route comparisons, heatmaps, and business impact estimates.

---

## 3. Strategic Alignment

The product must prioritize the logistics case requirements:

- delivery delay prediction;
- traffic, weather, hub dwell time, and driver/vehicle behavior features;
- multi-objective route optimization;
- route objectives covering time, fuel, carbon emission, and SLA risk;
- shipment-level carbon footprint;
- near-real-time SLA risk scores and automated alerts;
- hub congestion pattern analysis and bottleneck detection;
- integration of GPS/IoT-like, ERP/TMS-like, traffic, and weather data;
- near-real-time processing and decision support;
- carbon analytics;
- fleet utilization insights;
- business impact estimation.

The original project ideas are preserved as supporting capabilities:

- YOLO-based loading analysis;
- loading compliance and high-load pattern detection;
- motor/last-mile fleet focus;
- vehicle usage history;
- behavior-based preventive maintenance recommendations.

The official logistics case requirements are primary. Loading AI and predictive maintenance must support the larger green and resilient logistics story rather than replace it.

---

## 4. Product Scope

### 4.1 MVP Scope

The MVP includes:

- Streamlit web frontend;
- FastAPI backend;
- REST API communication;
- SQLite relational database;
- local file-based data lake for historical CSV/Parquet snapshots;
- simulated near-real-time event ingestion;
- seeded synthetic logistics datasets;
- three integrated modules;
- YOLO loading detector integration with explicit demo fallback;
- delivery delay regression;
- SLA risk classification;
- multi-objective route optimization;
- shipment/route carbon calculation;
- hub congestion scoring and bottleneck detection;
- fleet utilization insights;
- behavior-based maintenance recommendation;
- decision engine;
- automated rule-based alerts;
- dashboard, maps, heatmaps, charts, and reports;
- model evaluation pages or panels;
- API and unit tests;
- architecture and workflow documentation.

### 4.2 Out of Scope for MVP

The MVP does not require:

- production Blibli data;
- connection to actual Blibli ERP/TMS;
- real GPS hardware;
- real IoT sensors;
- paid traffic APIs;
- paid weather APIs;
- live customer data;
- full Kafka infrastructure;
- Kubernetes;
- a true distributed data lake;
- mobile applications;
- authentication or role-based access control;
- automated driver dispatch;
- real financial settlement;
- production carbon certification;
- guaranteed mechanical failure prediction;
- safety-critical autonomous decisions.

### 4.3 Future Scope

Possible future additions:

- real traffic and weather APIs;
- real GPS event streaming;
- Kafka or Redpanda;
- PostgreSQL;
- TimescaleDB;
- Redis;
- multi-region data processing;
- live ERP/TMS connectors;
- reinforcement learning for continuous rerouting;
- graph road-network routing;
- multi-vehicle and multi-depot optimization;
- driver mobile app;
- SHAP-based local explainability;
- real camera streams;
- calibrated package dimension estimation;
- real vehicle telemetry;
- validated RUL models;
- carbon accounting aligned with a selected reporting standard.

---

## 5. Target Users

### 5.1 Logistics Control Tower Operator

Primary needs:

- see at-risk shipments;
- understand predicted delay;
- monitor SLA risk;
- inspect active alerts;
- compare route recommendations;
- understand why the system is recommending an action.

### 5.2 Dispatcher / Route Planner

Primary needs:

- upload or simulate delivery batches;
- review route candidates;
- compare fastest, greenest, and balanced routes;
- inspect distance, time, fuel, CO₂, and SLA risk;
- save a recommended route.

### 5.3 Hub Operations Manager

Primary needs:

- view hub congestion risk;
- inspect queue growth and dwell time;
- detect bottleneck stages;
- identify peak congestion periods;
- estimate shipment impact.

### 5.4 Fleet Manager

Primary needs:

- understand fleet utilization;
- inspect high-load and high-distance usage;
- monitor vehicle operational health indicators;
- receive preventive check-up recommendations.

### 5.5 Warehouse / Loading Operator

Primary needs:

- inspect loading image;
- detect package/loading objects;
- receive loading compliance warnings;
- record high-load or unsafe patterns.

### 5.6 Management / Competition Judge

Primary needs:

- understand the system within minutes;
- see measurable model performance;
- see architecture and workflow;
- understand business impact;
- distinguish synthetic data from real data;
- see how all three modules are integrated.

---

## 6. Core Problem Statement

### P1 — Delivery operations are reactive

Traffic, weather, hub delays, and changing operating conditions can make deliveries late. Operators often react after the delay becomes visible.

**Product response:** predict delay and SLA risk before breach.

### P2 — Route decisions involve conflicting objectives

The shortest route is not always the best route. A route can be shorter but slower, higher-emission, or more likely to breach SLA.

**Product response:** compare route candidates across time, fuel, CO₂, and SLA risk.

### P3 — Operational bottlenecks are distributed across the network

A congested hub, repeated overload patterns, poor fleet utilization, or worsening vehicle usage can create cascading delay.

**Product response:** detect hub bottlenecks and fleet resilience risks before they become larger disruptions.

### P4 — Operational data is fragmented

Traffic, weather, GPS, shipment, hub, loading, and vehicle history are often analyzed separately.

**Product response:** integrate them into one data and decision pipeline.

---

# 7. MODULE 1 — DELIVERY & LOADING RISK AI

## 7.1 Module Purpose

Module 1 answers:

> Is this shipment likely to be delayed, breach SLA, or show an operational loading risk?

It contains three coordinated capabilities:

1. Loading Risk Vision
2. Delivery Delay Prediction
3. SLA Risk Classification

---

## 7.2 Capability A — Loading Risk Vision

### Goal

Use YOLO to detect loading/package objects from warehouse or loading images and derive loading risk indicators.

### Initial classes

Configurable initial classes:

- `small_box`
- `medium_box`
- `large_box`
- `delivery_bag`
- `loose_package`
- `strap`
- `motorcycle`
- `van_loading_area`

The exact training classes may be revised after dataset inspection.

### Functional requirements

**M1-L01** User can upload JPG, JPEG, or PNG.  
**M1-L02** System validates file type, size, and image readability.  
**M1-L03** System loads a configured Ultralytics YOLO model.  
**M1-L04** YOLO model path is replaceable without changing business logic.  
**M1-L05** Low-confidence detections are filtered by configurable threshold.  
**M1-L06** System returns normalized detections, not raw Ultralytics result objects.  
**M1-L07** System counts package/loading classes.  
**M1-L08** System derives loading indicators from detected classes and shipment load data.  
**M1-L09** System displays bounding boxes, labels, and confidence.  
**M1-L10** System calculates a loading compliance score using documented prototype rules.  
**M1-L11** System identifies warnings such as `Loose Package`, `No Strap Detected`, `High Load Pattern`, or `Review Required`.  
**M1-L12** System stores the inspection result.  
**M1-L13** If no custom YOLO model exists, the application must use a visibly labeled deterministic Demo Detection Mode.  
**M1-L14** Demo detections must never be described as real model inference.

### Important limitation

The vision model does not directly measure weight from pixels.

Shipment weight must come from shipment/ERP-like input data.

The camera module provides visual loading context and compliance indicators.

---

## 7.3 Capability B — Delivery Delay Prediction

### Goal

Predict delivery delay in minutes.

### Target

`delay_minutes`

The prediction may be:

- 0 for on-time/no predicted delay;
- positive for predicted lateness.

### Candidate model

MVP preferred order:

1. XGBoost Regressor if included and stable;
2. HistGradientBoostingRegressor or RandomForestRegressor as fallback.

The final model selection must be based on actual validation results, not preference.

### Input features

Potential features:

- historical_travel_time_min
- planned_travel_time_min
- current_traffic_index
- traffic_speed_ratio
- weather_condition
- rainfall_mm
- temperature_c
- hub_dwell_time_min
- normal_hub_dwell_time_min
- driver_speed_ratio
- stop_duration_min
- route_distance_km
- load_weight_kg
- vehicle_type
- shipment_priority
- hour_of_day
- day_of_week
- origin_hub
- destination_zone
- route_deviation_count
- loading_compliance_score

### Derived features

Examples:

```text
traffic_delay_ratio =
historical_travel_time_min / max(planned_travel_time_min, epsilon)

hub_dwell_excess =
hub_dwell_time_min - normal_hub_dwell_time_min

sla_buffer_minutes =
sla_deadline - current_estimated_arrival

speed_deviation =
actual_average_speed / expected_average_speed
```

### Functional requirements

**M1-D01** System accepts current shipment context.  
**M1-D02** System aggregates traffic, weather, shipment, GPS-like, and hub features.  
**M1-D03** Feature pipeline handles missing values using documented strategies.  
**M1-D04** System predicts delay minutes.  
**M1-D05** Negative predicted delay is clipped to 0 unless early-arrival modeling is explicitly enabled.  
**M1-D06** System displays model source and version.  
**M1-D07** System displays actual model metrics from metadata when available.  
**M1-D08** System displays major risk factors based on real feature values.  
**M1-D09** Prediction is stored with timestamp and input snapshot reference.  
**M1-D10** Missing model activates an explicitly labeled rules/demo fallback.

### Evaluation

Primary:

- MAE
- RMSE

Secondary:

- R²

Do not use classification accuracy for delay regression.

---

## 7.4 Capability C — SLA Risk Classification

### Goal

Estimate the probability that a shipment will breach its SLA.

### Output

- SLA risk probability: `0.00–1.00`
- Risk level:
  - Low
  - Medium
  - High
  - Critical

### Example thresholds

Configurable prototype thresholds:

- Low: `< 0.25`
- Medium: `0.25–<0.50`
- High: `0.50–<0.75`
- Critical: `>=0.75`

### Candidate model

- XGBoost Classifier, RandomForestClassifier, or HistGradientBoostingClassifier.

Model selection must be validation-driven.

### Input features

SLA model may consume:

- current operational features;
- predicted delay minutes;
- SLA buffer;
- traffic index;
- weather severity;
- hub dwell excess;
- route distance;
- shipment priority;
- vehicle type;
- loading risk indicators.

### Functional requirements

**M1-S01** System generates SLA breach probability.  
**M1-S02** System maps probability to a configurable risk level.  
**M1-S03** System identifies at-risk shipments.  
**M1-S04** High and Critical results generate alerts through the decision engine.  
**M1-S05** System stores SLA prediction history.  
**M1-S06** System shows major contributing operational factors.  
**M1-S07** System supports batch scoring for a shipment table.  
**M1-S08** System supports simulated near-real-time rescoring when a traffic, weather, GPS, or hub event changes.

### Evaluation

Primary:

- F1-score
- Macro F1

Also display:

- precision
- recall
- confusion matrix
- ROC-AUC when class/probability structure is suitable

For the at-risk class, recall must be inspected explicitly.

---

## 7.5 Module 1 Combined Output

Example:

```json
{
  "shipment_id": "SHP-1028",
  "loading": {
    "compliance_score": 82,
    "status": "Warning",
    "main_warning": "High load pattern"
  },
  "delay_prediction": {
    "predicted_delay_minutes": 38,
    "model": "delay_model_v1"
  },
  "sla_risk": {
    "probability": 0.81,
    "level": "Critical",
    "model": "sla_model_v1"
  },
  "main_factors": [
    "Traffic index is 0.89",
    "Hub dwell exceeds normal by 42 minutes",
    "Rainfall is high",
    "SLA buffer is below predicted delay"
  ]
}
```

---

# 8. MODULE 2 — GREEN MULTI-OBJECTIVE ROUTE OPTIMIZER

## 8.1 Module Purpose

Module 2 answers:

> Which route best balances speed, fuel, carbon emissions, and SLA reliability?

The module must not be presented as a shortest-path-only system.

---

## 8.2 Route Inputs

Required entities:

### Shipment

- shipment_id
- origin
- destination
- load_weight_kg
- load_volume_liter
- priority
- SLA deadline
- package category

### Vehicle

- vehicle_id
- vehicle_type
- capacity_weight_kg
- capacity_volume_liter
- fuel_type
- fuel_efficiency_km_per_liter
- current_status

### Route / edge context

- route candidate ID
- sequence
- distance_km
- expected_travel_time_min
- traffic index
- weather severity
- known hub stops
- current SLA risk

---

## 8.3 Capacity Validation

Before optimization:

```text
total_weight <= vehicle_weight_capacity
total_volume <= vehicle_volume_capacity
```

If invalid:

- route planning is blocked for the selected vehicle;
- user receives a clear capacity warning;
- system suggests selecting another vehicle or splitting the batch.

No invalid route may be silently recommended.

---

## 8.4 Carbon Calculation

The system must calculate estimated shipment/route carbon footprint.

MVP baseline:

```text
estimated_fuel_liter = distance_km / fuel_efficiency_km_per_liter

base_co2_kg =
estimated_fuel_liter × configured_fuel_emission_factor

load_adjustment =
function(load_weight / vehicle_capacity)

estimated_co2_kg =
base_co2_kg × load_adjustment
```

All constants and assumptions are centralized and documented.

### Carbon regression model

To align with the requested AI scope, an optional Carbon Emission Regressor may estimate route emissions from:

- vehicle type;
- distance;
- load weight;
- fuel efficiency;
- traffic intensity;
- stop count.

When trained only on synthetic/formula-generated targets, the UI must disclose that its metrics reflect fit to synthetic carbon logic, not certified field emission measurements.

The deterministic carbon calculator remains available as the transparent baseline.

---

## 8.5 Multi-Objective Function

The optimizer minimizes normalized objectives:

```text
route_cost =
w_time   × normalized_time
+ w_fuel × normalized_fuel
+ w_co2  × normalized_co2
+ w_sla  × normalized_sla_risk
```

Requirements:

- all objective values must be normalized before weighted summation;
- weights must sum to 1.0 within tolerance;
- presets must be transparent;
- the user may edit weights in an advanced control;
- the system must show the exact weights used.

### Presets

#### Fastest

```text
time  = 0.60
fuel  = 0.10
co2   = 0.05
sla   = 0.25
```

#### Greenest

```text
time  = 0.10
fuel  = 0.25
co2   = 0.55
sla   = 0.10
```

#### SLA Priority

```text
time  = 0.20
fuel  = 0.05
co2   = 0.05
sla   = 0.70
```

#### Balanced AI

```text
time  = 0.30
fuel  = 0.20
co2   = 0.20
sla   = 0.30
```

These are prototype presets and must be labeled as configurable decision-policy weights.

---

## 8.6 Optimization Engines

### Baseline — OR-Tools

Purpose:

- establish a deterministic distance/capacity benchmark;
- provide a fallback route.

### Main optimizer — Genetic Algorithm

The GA should support a route chromosome representing stop sequence.

Core components:

- population initialization;
- fitness evaluation;
- selection;
- crossover;
- mutation;
- elitism;
- stopping criterion.

Fitness uses the multi-objective route cost.

### Future advanced mode — Reinforcement Learning

PPO or other adaptive rerouting is deferred unless time and data quality permit.

It must not block MVP completion.

---

## 8.7 Dynamic / Near-Real-Time Reoptimization

The competition prototype should simulate dynamic updates.

Possible update events:

- traffic index increases;
- weather becomes severe;
- hub congestion increases;
- GPS progress shows route deviation;
- SLA risk changes.

Flow:

```text
NEW EVENT
   ↓
UPDATE OPERATIONAL SNAPSHOT
   ↓
RESCORE DELAY / SLA
   ↓
RECALCULATE ROUTE CANDIDATE COSTS
   ↓
IF RECOMMENDATION CHANGES
   ↓
CREATE ROUTE RECOMMENDATION ALERT
```

The prototype may use a configurable event playback simulator instead of real external APIs.

---

## 8.8 Route Outputs

For each route candidate:

- route name;
- stop sequence;
- distance;
- estimated time;
- estimated fuel;
- estimated CO₂;
- SLA risk;
- objective score;
- objective weights;
- estimated on-time probability.

Required comparison:

- Original / current route;
- OR-Tools baseline;
- Fastest;
- Greenest;
- Balanced AI.

### Recommended route

The decision engine selects or highlights one route based on the active decision policy.

Example:

```text
Balanced AI Route
Time: 42 min
Fuel: 1.3 L
CO₂: 3.0 kg
SLA Risk: 8%
Overall Cost Score: 0.21

Recommendation:
Use Balanced AI Route.
It reduces SLA risk by 31 percentage points while using 14% less estimated fuel than the current route.
```

The explanation must be calculated from actual route metrics.

---

## 8.9 Module 2 Evaluation

Measure:

- distance reduction;
- fuel reduction estimate;
- CO₂ reduction estimate;
- SLA risk reduction;
- on-time probability improvement;
- GA objective score versus baseline;
- optimizer runtime.

No fixed improvement percentage may be fabricated.

---

# 9. MODULE 3 — NETWORK & FLEET RESILIENCE AI

## 9.1 Module Purpose

Module 3 answers:

> Which hub or vehicle is becoming an operational risk before it causes larger disruption?

It contains:

1. Hub Congestion & Bottleneck Intelligence
2. Fleet Utilization Intelligence
3. Behavior-Based Preventive Maintenance

The hub analysis is the primary competition-aligned capability. Maintenance is a supporting fleet-resilience feature.

---

## 9.2 Capability A — Hub Congestion Intelligence

### Input features

- hub_id
- timestamp
- shipment_arrival_count
- shipment_departure_count
- arrival_rate_per_hour
- departure_rate_per_hour
- queue_size
- average_dwell_time_min
- normal_dwell_time_min
- processing_rate_per_hour
- sorting_time_min
- loading_time_min
- unloading_time_min
- workforce_capacity_index
- current_delayed_shipments

### Derived features

```text
queue_growth =
arrival_rate_per_hour - departure_rate_per_hour

dwell_excess =
average_dwell_time_min - normal_dwell_time_min

processing_utilization =
arrival_rate_per_hour / max(processing_rate_per_hour, epsilon)

delay_pressure =
current_delayed_shipments / max(current_total_shipments, 1)
```

### Congestion output

- congestion score `0–100`;
- risk level:
  - Normal
  - Watch
  - High
  - Critical
- estimated delayed shipment impact;
- bottleneck stage;
- major factors.

### Bottleneck detection

Candidate stages:

- inbound receiving;
- unloading;
- sorting;
- staging;
- loading;
- outbound dispatch.

The MVP may detect the bottleneck using relative process-time deviation and queue accumulation.

Example:

```text
sorting_deviation =
current_sorting_time / normal_sorting_time
```

The stage with the largest operational deviation, subject to configurable minimum thresholds, may be flagged as the likely bottleneck.

The UI must say `Likely Bottleneck` or `Detected Operational Bottleneck Indicator`, not claim certain root cause.

### Pattern detection

The system should analyze time windows such as:

- hourly;
- 4-hour block;
- daily.

It should display:

- congestion trend;
- peak hours;
- dwell trend;
- queue growth;
- risk heatmap.

### Optional AI model

Isolation Forest or a supervised congestion classifier may flag anomalous hub states.

A transparent congestion score remains the baseline and fallback.

---

## 9.3 Capability B — Fleet Utilization Intelligence

Calculate:

- active vehicle ratio;
- route distance per vehicle;
- shipment count per vehicle;
- load utilization;
- high-load trip count;
- idle vehicle count;
- fleet utilization score.

Example:

```text
fleet_utilization =
active_vehicle_hours / available_vehicle_hours
```

The system should identify:

- underused vehicles;
- overloaded/high-use vehicles;
- uneven work distribution.

---

## 9.4 Capability C — Behavior-Based Preventive Maintenance

### Purpose

Use operational history as a low-cost preventive check-up recommendation.

This is not mechanical failure certainty.

### Inputs

- current_km
- km_at_last_service
- days_since_last_service
- average_daily_km
- total_route_distance
- high-load_trip_count
- route_deviation_count
- average_speed_trend
- fuel_efficiency_trend
- late_delivery_rate
- past_breakdowns
- maintenance_count
- vehicle_age_months

### Outputs

- operational health score `0–100`;
- maintenance risk:
  - Normal
  - Needs Attention
  - Check-Up Soon
  - Service Recommended
- recommended check-up window;
- factor summary.

### MVP methodology

1. transparent rule-based operational health score;
2. optional RandomForestClassifier for maintenance risk;
3. optional regressor for days until recommended check-up.

If targets are synthetic, model metrics must be labeled as synthetic-target metrics.

Do not use the term Remaining Useful Life unless the target is genuinely defined as RUL from suitable degradation/failure data.

Use `Estimated Days Until Recommended Check-Up` for synthetic operational targets.

---

## 9.5 Module 3 Integrated Output

Example:

```json
{
  "hub": {
    "hub_id": "HUB-CBT",
    "congestion_score": 92,
    "risk_level": "Critical",
    "likely_bottleneck": "Sorting",
    "estimated_delayed_shipments": 26
  },
  "fleet": {
    "fleet_utilization_percent": 78,
    "underused_vehicle_count": 3,
    "high_use_vehicle_count": 4
  },
  "vehicle_risk": {
    "vehicle_id": "MTR-002",
    "health_score": 58,
    "maintenance_risk": "Check-Up Soon",
    "recommended_checkup_days": 12
  }
}
```

---

# 10. DECISION ENGINE

## 10.1 Purpose

The decision engine converts predictions into operational recommendations.

Models predict.

The decision engine applies operational policy.

The decision engine must be deterministic, transparent, and configurable.

---

## 10.2 Decision Rules

Example SLA alert rules:

```text
IF sla_risk >= critical_threshold:
    create CRITICAL SLA alert

ELIF sla_risk >= high_threshold:
    create HIGH SLA alert
```

Example route recommendation rule:

```text
IF current_route_sla_risk - balanced_route_sla_risk >= configured_delta
AND balanced_route_co2 <= current_route_co2 × allowed_co2_multiplier:
    recommend balanced route
```

Example hub rule:

```text
IF congestion_score >= 80
AND queue_growth > 0:
    create hub congestion alert
```

Example fleet rule:

```text
IF maintenance_risk == "Service Recommended":
    create preventive check-up alert
```

---

## 10.3 Alert Levels

- Info
- Watch
- Warning
- Critical

Each alert stores:

- alert_id;
- alert_type;
- entity_type;
- entity_id;
- severity;
- title;
- message;
- recommendation;
- created_at;
- status;
- acknowledged_at.

---

# 11. SYSTEM DATA SOURCES

The prototype supports eight logical data sources.

### DS1 — Shipment / ERP-like data

- shipment metadata;
- SLA;
- weight;
- priority;
- origin/destination.

### DS2 — TMS / route data

- current route;
- planned time;
- vehicle assignment;
- stop sequence.

### DS3 — Traffic data

- traffic index;
- average road speed;
- travel-time multiplier.

### DS4 — Weather data

- weather condition;
- rainfall;
- temperature;
- wind where available.

### DS5 — GPS / vehicle movement

- vehicle position;
- speed;
- timestamp;
- route deviation.

### DS6 — Hub operational data

- arrivals;
- departures;
- queue;
- dwell;
- process times.

### DS7 — Camera/loading data

- image;
- detected classes;
- compliance indicators.

### DS8 — Fleet/service history

- odometer;
- fuel efficiency;
- service history;
- breakdown history.

For the MVP, data may be synthetic or simulated. Every synthetic source must be labeled.

---

# 12. DATA INGESTION

## 12.1 Batch Ingestion

Supported:

- CSV upload;
- seed scripts;
- generated demo datasets.

Use cases:

- historical training data;
- shipments;
- vehicles;
- hubs;
- maintenance history.

## 12.2 Simulated Stream Ingestion

The application should include an event simulator.

Event types:

- TRAFFIC_UPDATE
- WEATHER_UPDATE
- GPS_UPDATE
- HUB_UPDATE
- SHIPMENT_UPDATE

The simulator replays time-ordered events.

Possible interval:

- manual next-event button;
- auto-play every 2–5 seconds.

Near-real-time means that new events can trigger rescoring and decision updates within the prototype process.

Do not claim production streaming latency.

---

# 13. STORAGE REQUIREMENTS

## 13.1 Relational Database

MVP: SQLite.

Logical tables:

- shipments
- vehicles
- hubs
- routes
- route_candidates
- traffic_snapshots
- weather_snapshots
- gps_events
- hub_events
- loading_inspections
- loading_detections
- delay_predictions
- sla_predictions
- carbon_estimates
- route_recommendations
- alerts
- maintenance_history
- breakdown_history
- maintenance_predictions
- model_registry
- simulation_events

## 13.2 Local Data Lake

Use:

```text
data/
  raw/
  interim/
  processed/
  demo/
```

CSV or Parquet files may hold:

- generated training sets;
- batch snapshots;
- model evaluation output.

The local data lake is an MVP simulation of the proposed data-lake layer.

---

# 14. WEB APPLICATION PAGES

## Page 1 — Command Center

Must show:

- active shipments;
- High/Critical SLA risk count;
- predicted delayed shipments;
- critical hubs;
- estimated CO₂ today;
- fleet utilization;
- alert feed;
- risk map or shipment map;
- SLA risk distribution;
- hub congestion heatmap;
- route/carbon trend.

## Page 2 — Delivery Risk AI

Must show:

- shipment selector;
- input feature summary;
- loading inspection panel;
- image upload;
- delay prediction;
- SLA risk probability;
- risk level;
- main factors;
- prediction history;
- generated alerts.

## Page 3 — Green Route Optimizer

Must show:

- delivery batch or shipment selection;
- vehicle selector;
- capacity validation;
- objective preset selector;
- editable weights;
- current route;
- OR-Tools route;
- Fastest;
- Greenest;
- Balanced AI;
- metrics comparison;
- route map;
- carbon comparison;
- recommendation explanation;
- reoptimization simulation.

## Page 4 — Network Resilience

Must show:

- hub selector;
- hub congestion score;
- queue growth;
- dwell time;
- likely bottleneck;
- peak periods;
- hub heatmap;
- at-risk hub table;
- fleet utilization;
- vehicle usage distribution;
- maintenance risk panel.

## Page 5 — Live Simulation

Must show:

- simulation controls;
- current simulation timestamp;
- event stream;
- active shipment state;
- active traffic/weather/hub conditions;
- rescored SLA risk;
- changed route recommendation;
- generated alerts.

## Page 6 — Analytics & Impact

Must show:

- route distance reduction;
- estimated fuel reduction;
- estimated CO₂ reduction;
- SLA risk change;
- on-time prediction change;
- fleet utilization insights;
- business impact assumptions;
- model performance cards.

## Page 7 — Data & Model Registry

Must show:

- data source labels;
- synthetic/real status;
- model versions;
- training rows;
- metrics;
- model availability;
- fallback status;
- limitations.

## Page 8 — Reports

Must support:

- route comparison export;
- shipment risk export;
- hub risk export;
- alert export;
- executive summary CSV/JSON;
- printable summary view.

PDF is optional.

---

# 15. FRONTEND REQUIREMENTS

- Streamlit wide layout.
- No direct database access.
- No direct model loading.
- No optimization inside pages.
- All business operations through FastAPI.
- API client centralized.
- Consistent cards and badges.
- Clear synthetic data badge.
- Clear estimate/prediction labels.
- Loading and error states.
- No dead buttons.
- No placeholder metric values in final MVP.
- Empty states must guide the user.
- Route maps and heatmaps must have legends.

---

# 16. BACKEND REQUIREMENTS

FastAPI backend responsibilities:

- request validation;
- API routing;
- service orchestration;
- dependency construction;
- standardized errors;
- health/model status.

API handlers must remain thin.

Services:

- DataIngestionService
- ShipmentService
- LoadingRiskService
- DeliveryRiskService
- RouteOptimizationService
- CarbonService
- HubRiskService
- FleetResilienceService
- DecisionEngineService
- AlertService
- SimulationService
- AnalyticsService
- ReportService

Repositories are the database access boundary.

---

# 17. CORE API REQUIREMENTS

Minimum endpoints:

```text
GET  /health
GET  /api/vehicles
GET  /api/shipments
GET  /api/hubs

POST /api/loading/analyze
GET  /api/loading/history/{shipment_id}

POST /api/risk/predict/{shipment_id}
POST /api/risk/predict-batch
GET  /api/risk/history/{shipment_id}

POST /api/routes/optimize
POST /api/routes/reoptimize
GET  /api/routes/{shipment_id}/candidates
POST /api/routes/recommend

POST /api/carbon/estimate

POST /api/hubs/analyze/{hub_id}
GET  /api/hubs/risk
GET  /api/hubs/{hub_id}/history

POST /api/fleet/analyze
POST /api/maintenance/analyze/{vehicle_id}

GET  /api/alerts
PATCH /api/alerts/{alert_id}/acknowledge

POST /api/simulation/reset
POST /api/simulation/next
POST /api/simulation/play
POST /api/simulation/pause
GET  /api/simulation/state

GET  /api/analytics/summary
GET  /api/models
GET  /api/reports/executive-summary
```

---

# 18. AI / MODEL REQUIREMENTS

## 18.1 YOLO

Metrics:

- mAP50
- mAP50-95
- precision
- recall
- confusion matrix

Target:

- mAP50 ≥ 85% is a target, not a guaranteed result.

## 18.2 Delay regression

Metrics:

- MAE
- RMSE
- R²

## 18.3 SLA classification

Metrics:

- F1
- Macro F1
- precision
- recall
- confusion matrix
- ROC-AUC when appropriate

## 18.4 Carbon regression

Metrics:

- MAE
- RMSE
- R²

Synthetic-target disclosure required when applicable.

## 18.5 Hub anomaly / risk model

Metrics depend on model.

For supervised classification:

- F1
- precision
- recall

For Isolation Forest:

- anomaly score distribution;
- test scenario detection rate;
- no fabricated classification accuracy.

## 18.6 Maintenance model

Metrics:

- classification F1 when classifier used;
- MAE/RMSE for days-to-check-up regression.

Synthetic-target disclosure required if applicable.

---

# 19. NON-FUNCTIONAL REQUIREMENTS

**NF-01 Honesty:** Synthetic data, simulated events, estimates, and model predictions are labeled.

**NF-02 Modularity:** Frontend, API, services, algorithms/models, and repositories remain separate.

**NF-03 Testability:** Core formulas and algorithms are unit-testable without Streamlit.

**NF-04 Graceful degradation:** Missing YOLO or ML files must activate clearly labeled fallback behavior.

**NF-05 Responsiveness:** Normal dashboard operations should respond within a few seconds on a laptop.

**NF-06 Reproducibility:** Seeds and model metadata are stored.

**NF-07 Observability:** Backend logs prediction, optimization, and decision events.

**NF-08 Input validation:** All uploaded files and API payloads are validated.

**NF-09 Security baseline:** File size limits, extension checks, safe filenames, no arbitrary path access.

**NF-10 Accessibility:** Status information must use text labels in addition to color.

**NF-11 Configurability:** Objective weights, thresholds, model paths, and data paths are centralized.

**NF-12 Timezone:** Asia/Jakarta for displayed operational timestamps.

---

# 20. SUCCESS CRITERIA

## Overall

The complete demo must show:

```text
SIMULATED LOGISTICS EVENT
        ↓
DELIVERY DELAY + SLA RESCORING
        ↓
HUB / NETWORK RISK UPDATE
        ↓
MULTI-OBJECTIVE ROUTE REOPTIMIZATION
        ↓
CARBON + SLA COMPARISON
        ↓
DECISION ENGINE RECOMMENDATION
        ↓
AUTOMATED ALERT
        ↓
DASHBOARD UPDATE
```

## Module 1

- loading image can be analyzed;
- delay prediction works;
- SLA risk score works;
- High/Critical SLA alerts work;
- actual metrics are displayed;
- factors trace to input data.

## Module 2

- route candidates are generated;
- OR-Tools baseline works;
- GA multi-objective optimizer works;
- time/fuel/CO₂/SLA are calculated;
- objective weights are visible;
- dynamic event can trigger reoptimization;
- route recommendation explanation uses actual metrics.

## Module 3

- hub congestion score works;
- bottleneck indicator works;
- peak risk periods are visible;
- hub risk heatmap works;
- fleet utilization metrics work;
- maintenance recommendation works as a supporting feature.

## Business impact

The analytics page must estimate:

- distance reduction;
- fuel reduction;
- CO₂ reduction;
- SLA risk reduction;
- fleet utilization changes.

All business impact results must state the baseline and assumptions.

---

# 21. END-TO-END DEMO SCENARIO

1. Start with shipment `SHP-1028`.
2. Shipment travels from Hub A through Hub B to a delivery zone.
3. Initial traffic is moderate.
4. Initial weather is clear.
5. Initial SLA risk is Medium.
6. Current route is displayed.
7. A loading inspection is shown or uploaded.
8. Simulator advances.
9. Traffic event changes to severe congestion.
10. Weather event changes to heavy rain.
11. Hub B dwell time increases and queue begins to grow.
12. Module 3 marks Hub B as High/Critical congestion risk.
13. Module 1 updates predicted delay and SLA risk.
14. SLA risk becomes High or Critical.
15. Decision engine creates an SLA alert.
16. Module 2 recalculates route candidates.
17. Current route, Fastest, Greenest, and Balanced AI are compared.
18. Balanced AI route reduces SLA risk with a measurable CO₂ trade-off.
19. Decision engine recommends a route.
20. Dashboard and event feed update.
21. Analytics show expected SLA, fuel, and carbon impact.
22. Fleet panel shows which vehicle is heavily utilized and whether preventive check-up attention is recommended.

The numerical values must come from computation, not hardcoded demonstration claims.

---

# 22. ASSUMPTIONS

- The prototype uses synthetic or simulated logistics data unless an external source is explicitly connected.
- Jakarta/Jabodetabek is the default demo geography.
- Traffic and weather may be simulated.
- GPS is represented as timestamped vehicle events.
- Shipment deadlines are synthetically generated.
- Carbon factors are configurable prototype estimates.
- The route objective weights are policy choices, not learned truths.
- Maintenance recommendations are operational risk recommendations.
- The system is a decision-support platform; a human operator remains responsible for action.
- The dataset size and model quality determine actual performance.
- The project must never hardcode success metrics.

---

# 23. LIMITATIONS

- Haversine or simplified route matrices do not equal real road-network travel.
- Synthetic traffic/weather patterns cannot reproduce all real disruptions.
- Synthetic model metrics do not prove field performance.
- Camera-based loading analysis depends on camera angle and dataset quality.
- Carbon estimates depend on assumptions and emission factors.
- Driver behavior features may be simplified.
- Hub bottleneck indicators are operational signals, not definitive causal proof.
- Extreme events and regulations may not be predictable.
- Real-time production reliability requires infrastructure outside MVP scope.

---

# 24. FINAL MVP DEFINITION

LogiSense AI MVP is complete when a user can run the web application, load the synthetic demo environment, inspect a shipment, simulate logistics events, observe delay/SLA risk changes, analyze loading risk, compare multi-objective route candidates, receive an AI-assisted route recommendation, inspect shipment-level carbon estimates, detect hub congestion and bottlenecks, view fleet resilience indicators, and export an executive impact summary from one integrated command center.
