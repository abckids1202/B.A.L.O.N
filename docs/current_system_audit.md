# Current System Audit

| Subsystem | Implementation | API | Frontend Usage | Data Source | Model Source | Status | Weakness | Repair |
|---|---|---|---|---|---|---|---|---|
| Delivery risk | backend/services/core.py + modules/delivery_risk | /api/risk/predict/{shipment_id} | Delivery Risk | SQLite demo providers | Trained artifacts when present, rule fallback otherwise | PARTIALLY FUNCTIONAL | Provenance was ambiguous | Runtime model loader and OperationalSnapshot added |
| Route optimization | modules/routing/optimizer.py | /api/routes/optimize | Route Optimizer | Demo route + traffic/weather providers | Deterministic optimizer | PARTIALLY FUNCTIONAL | Matrix/provider source hidden | Response now exposes matrix, traffic, weather, and policy |
| Hub intelligence | modules/hub_risk/analyzer.py | /api/hubs/analyze/{hub_id} | Network Resilience | DemoHubProvider | Transparent formula | FULLY FUNCTIONAL | Bottleneck overconfident in normal states | Significance guard added |
| Fleet utilization | modules/fleet/analyzer.py | /api/fleet/analyze | Network Resilience | DemoVehicleProvider | Formula | UI INCOMPLETE | Raw JSON primary display | Metric cards added |
| Simulation | backend/services/core.py | /api/simulation/next | Live Simulation | Demo provider tables | Same risk/route services | PARTIALLY FUNCTIONAL | Raw JSON presentation | Simulation summary cards added |
| Providers | modules/providers | /api/providers/status | Command Center, Data & Models | SQLite demo state | n/a | PARTIALLY FUNCTIONAL | Missing abstraction | Demo provider contracts and statuses added |
