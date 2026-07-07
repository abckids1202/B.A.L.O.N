# Model Training Data

## Delay

Target: `delay_minutes`.
Preferred real target: `max(0, actual_arrival_at - planned_arrival_at)`.
Prototype source: synthetic feature generator in `scripts/model_training_common.py`.
Metrics: MAE, RMSE, R2.
Leakage note: actual arrival and future hub/traffic state are excluded from runtime features.

## SLA

Target: `sla_breached`.
Preferred real target: `actual_arrival_at > sla_deadline`.
Prototype source: synthetic target logic.
Metrics: F1, Macro F1, precision, recall.

## YOLO

Current status: deterministic demo mode. Real training requires team-collected annotated images under `data/yolo`.
Weight must come from ERP/package metadata or scale data, not camera-only inference.

## Carbon

Deterministic calculator is primary. Regression model is an experiment against a synthetic formula-derived target.
