# LogiSense AI — Detailed Task Plan

**Rule:** The team checks items only after implementation and verification.

---

# Phase 0 — Planning Freeze

- [ ] Approve `prd.md`.
- [ ] Approve `styleguide.md`.
- [ ] Approve `architecture.md`.
- [ ] Approve `workflow.md`.
- [ ] Approve `implementation_plan.md`.
- [ ] Confirm product name.
- [ ] Confirm team roles.
- [ ] Confirm MVP deadline.
- [ ] Freeze three-module scope.
- [ ] Create Git repository.
- [ ] Create issue labels: backend, frontend, ML, data, optimization, docs, test.
- [ ] Create main/develop branch strategy.
- [ ] Define pull request review rule.

---

# Phase 1 — Repository Foundation

## Project structure

- [ ] Create `frontend/`.
- [ ] Create `backend/`.
- [ ] Create `modules/`.
- [ ] Create `database/`.
- [ ] Create `data/raw/`.
- [ ] Create `data/interim/`.
- [ ] Create `data/processed/`.
- [ ] Create `data/demo/`.
- [ ] Create `models/`.
- [ ] Create `scripts/`.
- [ ] Create `tests/`.
- [ ] Create `docs/`.

## Environment

- [ ] Create `.gitignore`.
- [ ] Create `.env.example`.
- [ ] Create `requirements.txt`.
- [ ] Create Python package `__init__.py` files.
- [ ] Create centralized settings loader.
- [ ] Configure `Asia/Jakarta` timezone.
- [ ] Add random seed configuration.
- [ ] Add model path configuration.
- [ ] Add database path configuration.
- [ ] Add simulator interval configuration.
- [ ] Add route objective preset configuration.
- [ ] Add risk threshold configuration.
- [ ] Add carbon factor configuration.
- [ ] Add upload size configuration.

## Logging

- [ ] Create backend logging config.
- [ ] Add request correlation ID.
- [ ] Log prediction events.
- [ ] Log optimization events.
- [ ] Log decision-engine events.
- [ ] Log fallback/model-unavailable events.

---

# Phase 2 — Database and Repositories

## Schema

- [ ] Create `shipments` table.
- [ ] Create `vehicles` table.
- [ ] Create `hubs` table.
- [ ] Create `routes` table.
- [ ] Create `route_candidates` table.
- [ ] Create `traffic_snapshots` table.
- [ ] Create `weather_snapshots` table.
- [ ] Create `gps_events` table.
- [ ] Create `hub_events` table.
- [ ] Create `loading_inspections` table.
- [ ] Create `loading_detections` table.
- [ ] Create `delay_predictions` table.
- [ ] Create `sla_predictions` table.
- [ ] Create `carbon_estimates` table.
- [ ] Create `route_recommendations` table.
- [ ] Create `alerts` table.
- [ ] Create `maintenance_history` table.
- [ ] Create `breakdown_history` table.
- [ ] Create `maintenance_predictions` table.
- [ ] Create `model_registry` table.
- [ ] Create `simulation_events` table.
- [ ] Enable SQLite foreign keys.
- [ ] Add required indexes.
- [ ] Add created/updated timestamps.

## Repositories

- [ ] Implement ShipmentRepository.
- [ ] Implement VehicleRepository.
- [ ] Implement HubRepository.
- [ ] Implement TrafficRepository.
- [ ] Implement WeatherRepository.
- [ ] Implement GPSRepository.
- [ ] Implement HubEventRepository.
- [ ] Implement LoadingRepository.
- [ ] Implement PredictionRepository.
- [ ] Implement RouteRepository.
- [ ] Implement CarbonRepository.
- [ ] Implement AlertRepository.
- [ ] Implement MaintenanceRepository.
- [ ] Implement ModelRegistryRepository.
- [ ] Implement SimulationRepository.

## Database scripts

- [ ] Create database initialization script.
- [ ] Make initialization idempotent.
- [ ] Create database reset script for demo.
- [ ] Verify empty-database startup.
- [ ] Verify repository tests against temporary DB.

---

# Phase 3 — Synthetic Demo Data

## Generators

- [ ] Create vehicle generator.
- [ ] Create hub generator.
- [ ] Create shipment generator.
- [ ] Create traffic snapshot generator.
- [ ] Create weather snapshot generator.
- [ ] Create GPS event generator.
- [ ] Create hub event generator.
- [ ] Create route baseline generator.
- [ ] Create loading inspection history generator.
- [ ] Create maintenance history generator.
- [ ] Create breakdown history generator.
- [ ] Create ordered simulation-event generator.

## Data quality

- [ ] Use fixed random seed.
- [ ] Generate realistic Jakarta/Jabodetabek coordinates.
- [ ] Generate Low/Medium/High/Critical SLA cases.
- [ ] Generate normal and congested hubs.
- [ ] Generate clear/rain/heavy-rain weather cases.
- [ ] Generate multiple vehicle types.
- [ ] Generate varying load weights.
- [ ] Generate varying fuel efficiencies.
- [ ] Generate known demo scenario `SHP-1028`.
- [ ] Label data as synthetic.
- [ ] Write dataset-generation rules to `docs/dataset.md`.

## Demo validation

- [ ] Confirm `SHP-1028` has ordered event progression.
- [ ] Confirm a traffic event increases delay pressure.
- [ ] Confirm a hub event increases congestion.
- [ ] Confirm at least one route recommendation changes after an event.
- [ ] Confirm analytics have non-empty baseline data.

---

# Phase 4 — FastAPI Foundation

- [ ] Create FastAPI app.
- [ ] Set title and version.
- [ ] Add CORS for local frontend.
- [ ] Add standardized API response/error schema.
- [ ] Add global exception handlers.
- [ ] Add `/health`.
- [ ] Report database health.
- [ ] Report YOLO model state.
- [ ] Report delay model state.
- [ ] Report SLA model state.
- [ ] Report carbon model state.
- [ ] Report maintenance model state.
- [ ] Register all API routers.
- [ ] Add API prefix `/api`.
- [ ] Add dependency factories.
- [ ] Add request validation.
- [ ] Verify Swagger documentation.

---

# Phase 5 — Module 1A: Loading Risk Vision

## Core module

- [ ] Define normalized Detection schema.
- [ ] Implement image validation.
- [ ] Implement image hashing.
- [ ] Implement YOLO detector wrapper.
- [ ] Load YOLO once.
- [ ] Filter confidence threshold.
- [ ] Normalize class names.
- [ ] Normalize bounding boxes.
- [ ] Return plain Python structures.
- [ ] Implement deterministic Demo Detection Mode.
- [ ] Derive deterministic demo seed from image hash.
- [ ] Implement annotated image renderer.
- [ ] Implement loading class counts.
- [ ] Implement prototype loading compliance score.
- [ ] Implement loading warning rules.
- [ ] Centralize loading rule thresholds.
- [ ] Unit test compliance scoring.

## Service and API

- [ ] Implement LoadingRiskService.
- [ ] Add `POST /api/loading/analyze`.
- [ ] Add loading history endpoint.
- [ ] Save loading inspection.
- [ ] Save detection rows.
- [ ] Return `is_demo`.
- [ ] Return model source.
- [ ] Return explicit demo disclosure.
- [ ] Handle missing YOLO model.
- [ ] Handle corrupt image.
- [ ] Handle unsupported file.

## YOLO training pipeline

- [ ] Create YOLO dataset folder documentation.
- [ ] Create `data.yaml` template.
- [ ] Create `train_yolo.py`.
- [ ] Create `evaluate_yolo.py`.
- [ ] Save evaluation metadata.
- [ ] Display mAP50.
- [ ] Display mAP50-95.
- [ ] Display precision.
- [ ] Display recall.
- [ ] Never hardcode YOLO metric values.

---

# Phase 6 — Module 1B: Delay Prediction

## Feature engineering

- [ ] Define delay feature schema.
- [ ] Implement categorical feature handling.
- [ ] Implement missing-value handling.
- [ ] Calculate traffic delay ratio.
- [ ] Calculate hub dwell excess.
- [ ] Calculate SLA buffer.
- [ ] Calculate speed deviation.
- [ ] Add time-of-day feature.
- [ ] Add day-of-week feature.
- [ ] Add loading compliance feature.
- [ ] Unit test feature calculations.

## Training

- [ ] Generate synthetic delay training target.
- [ ] Document target-generation rules.
- [ ] Split train/validation/test.
- [ ] Create baseline mean predictor.
- [ ] Train RandomForestRegressor.
- [ ] Train HistGradientBoostingRegressor.
- [ ] Add XGBoost only if dependency is approved.
- [ ] Compare MAE.
- [ ] Compare RMSE.
- [ ] Compare R².
- [ ] Select best validation model.
- [ ] Save selected model.
- [ ] Save preprocessing pipeline.
- [ ] Save feature names.
- [ ] Save model metadata.
- [ ] Save actual metrics.
- [ ] Add synthetic-target disclosure.

## Inference

- [ ] Implement DelayPredictor.
- [ ] Load model safely.
- [ ] Validate feature order.
- [ ] Clip invalid negative delay if configured.
- [ ] Implement rule fallback.
- [ ] Return model source.
- [ ] Return model version.
- [ ] Save prediction history.

---

# Phase 7 — Module 1C: SLA Risk

## Feature pipeline

- [ ] Define SLA feature schema.
- [ ] Include predicted delay.
- [ ] Include SLA buffer.
- [ ] Include traffic.
- [ ] Include weather.
- [ ] Include hub dwell excess.
- [ ] Include shipment priority.
- [ ] Include route context.
- [ ] Unit test SLA features.

## Training

- [ ] Generate SLA breach label.
- [ ] Document label-generation rule.
- [ ] Inspect class balance.
- [ ] Create baseline classifier.
- [ ] Train RandomForestClassifier.
- [ ] Train HistGradientBoostingClassifier.
- [ ] Add XGBoost only if approved.
- [ ] Evaluate accuracy.
- [ ] Evaluate F1.
- [ ] Evaluate Macro F1.
- [ ] Evaluate precision and recall.
- [ ] Inspect at-risk recall.
- [ ] Generate confusion matrix.
- [ ] Save best model.
- [ ] Save model metadata.

## Inference and alerts

- [ ] Implement SLA predictor.
- [ ] Return breach probability.
- [ ] Map probability to risk level.
- [ ] Centralize risk thresholds.
- [ ] Implement batch scoring.
- [ ] Save SLA prediction.
- [ ] Trigger decision engine for High/Critical.
- [ ] Unit test probability thresholds.

## API

- [ ] Add shipment risk prediction endpoint.
- [ ] Add batch-risk endpoint.
- [ ] Add prediction history endpoint.
- [ ] Return delay and SLA in one integrated response.

---

# Phase 8 — Carbon Engine

## Deterministic baseline

- [ ] Define fuel emission factors.
- [ ] Define vehicle categories.
- [ ] Calculate estimated fuel.
- [ ] Calculate base CO₂.
- [ ] Calculate load ratio.
- [ ] Implement load adjustment.
- [ ] Return assumptions.
- [ ] Unit test carbon calculation.

## Carbon regression

- [ ] Generate synthetic carbon dataset.
- [ ] Document target formula.
- [ ] Create baseline linear regression.
- [ ] Train RandomForestRegressor.
- [ ] Evaluate MAE.
- [ ] Evaluate RMSE.
- [ ] Evaluate R².
- [ ] Save model.
- [ ] Save metadata.
- [ ] Add synthetic-target disclosure.
- [ ] Implement fallback to deterministic baseline.

## API

- [ ] Add carbon estimate endpoint.
- [ ] Save carbon estimate.
- [ ] Return source: deterministic or ML.

---

# Phase 9 — Module 2: Route Optimization

## Route data

- [ ] Define route request schema.
- [ ] Define stop schema.
- [ ] Define route candidate schema.
- [ ] Validate duplicate IDs.
- [ ] Validate coordinates.
- [ ] Validate package weight.
- [ ] Validate volume.
- [ ] Validate vehicle capacity.
- [ ] Block invalid vehicle assignment.

## Distance and matrices

- [ ] Implement Haversine.
- [ ] Unit test same point.
- [ ] Unit test symmetry.
- [ ] Build distance matrix.
- [ ] Build estimated time matrix.
- [ ] Apply traffic multiplier.
- [ ] Apply weather multiplier.
- [ ] Document simplified distance limitation.

## Current/original route

- [ ] Define current route sequence.
- [ ] Calculate current route metrics.
- [ ] Calculate current route SLA risk.
- [ ] Calculate current route carbon.

## OR-Tools baseline

- [ ] Create OR-Tools solver.
- [ ] Scale distance costs correctly.
- [ ] Configure time limit.
- [ ] Return stop sequence.
- [ ] Return no-solution state.
- [ ] Add fallback behavior.
- [ ] Unit test solver.

## Genetic Algorithm

- [ ] Define chromosome.
- [ ] Implement population initialization.
- [ ] Implement route repair if required.
- [ ] Implement fitness function.
- [ ] Normalize objective values.
- [ ] Validate weights sum to 1.
- [ ] Implement selection.
- [ ] Implement crossover.
- [ ] Implement mutation.
- [ ] Implement elitism.
- [ ] Implement deterministic seed option.
- [ ] Implement generation stopping criterion.
- [ ] Store best score history.
- [ ] Unit test chromosome validity.
- [ ] Unit test all stops visited once.
- [ ] Unit test objective calculation.

## Decision presets

- [ ] Implement Fastest preset.
- [ ] Implement Greenest preset.
- [ ] Implement SLA Priority preset.
- [ ] Implement Balanced AI preset.
- [ ] Allow custom weights.
- [ ] Display exact weights.

## Route metrics

- [ ] Calculate distance.
- [ ] Calculate estimated time.
- [ ] Calculate estimated fuel.
- [ ] Calculate estimated CO₂.
- [ ] Calculate route SLA risk.
- [ ] Calculate normalized objective values.
- [ ] Calculate total objective score.
- [ ] Calculate baseline reduction percentages.
- [ ] Preserve negative improvement values.

## Route recommendation

- [ ] Implement recommendation rule.
- [ ] Compare candidate metrics.
- [ ] Generate quantitative explanation.
- [ ] Save route candidates.
- [ ] Save selected recommendation.

## API

- [ ] Add route optimize endpoint.
- [ ] Add route reoptimize endpoint.
- [ ] Add route candidates endpoint.
- [ ] Add route recommend endpoint.
- [ ] Return map-ready coordinates.
- [ ] Return candidate score histories where useful.

---

# Phase 10 — Module 3A: Hub Congestion

## Features

- [ ] Define hub event schema.
- [ ] Calculate arrival rate.
- [ ] Calculate departure rate.
- [ ] Calculate queue growth.
- [ ] Calculate dwell excess.
- [ ] Calculate processing utilization.
- [ ] Calculate delay pressure.
- [ ] Unit test derived features.

## Congestion score

- [ ] Define transparent congestion scoring formula.
- [ ] Centralize thresholds.
- [ ] Clamp score 0–100.
- [ ] Map score to risk level.
- [ ] Unit test normal hub.
- [ ] Unit test congested hub.

## Bottleneck detection

- [ ] Define process stages.
- [ ] Define normal process-time baselines.
- [ ] Calculate process deviations.
- [ ] Rank stage deviations.
- [ ] Apply minimum deviation threshold.
- [ ] Return likely bottleneck.
- [ ] Return evidence values.
- [ ] Unit test known sorting bottleneck scenario.

## Pattern analysis

- [ ] Aggregate hourly hub data.
- [ ] Aggregate 4-hour windows.
- [ ] Identify peak congestion period.
- [ ] Generate hub heatmap matrix.
- [ ] Generate dwell trend.
- [ ] Generate queue trend.

## Optional anomaly model

- [ ] Train Isolation Forest.
- [ ] Save model.
- [ ] Save metadata.
- [ ] Return anomaly score.
- [ ] Do not fabricate accuracy.

## API

- [ ] Add hub analyze endpoint.
- [ ] Add all-hub risk endpoint.
- [ ] Add hub history endpoint.
- [ ] Trigger hub alerts through decision engine.

---

# Phase 11 — Module 3B: Fleet Utilization

- [ ] Define active vehicle rule.
- [ ] Calculate active vehicle ratio.
- [ ] Calculate vehicle route distance.
- [ ] Calculate shipment count per vehicle.
- [ ] Calculate average load utilization.
- [ ] Calculate high-load trip count.
- [ ] Calculate idle vehicle count.
- [ ] Calculate fleet utilization score.
- [ ] Identify underused vehicles.
- [ ] Identify high-use vehicles.
- [ ] Generate utilization distribution.
- [ ] Add fleet analysis service.
- [ ] Add fleet analysis endpoint.

---

# Phase 12 — Module 3C: Preventive Maintenance

## Feature engineering

- [ ] Calculate km since last service.
- [ ] Calculate days since last service.
- [ ] Aggregate route distance.
- [ ] Aggregate high-load trips.
- [ ] Calculate fuel efficiency trend.
- [ ] Calculate speed trend.
- [ ] Count route deviations.
- [ ] Count breakdowns.
- [ ] Flag limited history.
- [ ] Unit test empty history.

## Rule engine

- [ ] Start health score at 100.
- [ ] Define prototype penalties.
- [ ] Penalize service-distance exposure.
- [ ] Penalize service-time exposure.
- [ ] Penalize high daily distance.
- [ ] Penalize high-load frequency.
- [ ] Penalize fuel efficiency decline.
- [ ] Penalize breakdown history.
- [ ] Clamp 0–100.
- [ ] Return triggered rules.
- [ ] Unit test healthy case.
- [ ] Unit test high-risk case.

## Optional ML

- [ ] Generate synthetic maintenance labels.
- [ ] Document synthetic target rules.
- [ ] Train RandomForestClassifier.
- [ ] Evaluate F1.
- [ ] Train check-up-days regressor.
- [ ] Evaluate MAE/RMSE.
- [ ] Save metadata.
- [ ] Add synthetic-target disclosure.
- [ ] Implement rule fallback.

## API

- [ ] Add vehicle maintenance analysis endpoint.
- [ ] Save maintenance recommendation.
- [ ] Return source provenance.

---

# Phase 13 — Decision Engine and Alerts

## Decision engine

- [ ] Define DecisionContext.
- [ ] Define DecisionResult.
- [ ] Implement SLA alert rule.
- [ ] Implement hub congestion alert rule.
- [ ] Implement route change recommendation rule.
- [ ] Implement fleet maintenance alert rule.
- [ ] Centralize decision thresholds.
- [ ] Ensure recommendations use computed metrics.
- [ ] Unit test each decision rule.

## Alerts

- [ ] Implement AlertService.
- [ ] Save alerts.
- [ ] Deduplicate repeated alerts.
- [ ] Add alert cooldown logic where appropriate.
- [ ] Add alert severity mapping.
- [ ] Add acknowledgement support.
- [ ] Add alerts list endpoint.
- [ ] Add acknowledge endpoint.
- [ ] Sort active alerts by severity and time.

---

# Phase 14 — Simulation Engine

- [ ] Define simulation state schema.
- [ ] Load ordered demo events.
- [ ] Implement reset.
- [ ] Implement next event.
- [ ] Implement previous state if feasible.
- [ ] Implement auto-play state.
- [ ] Implement pause.
- [ ] Apply traffic update.
- [ ] Apply weather update.
- [ ] Apply GPS update.
- [ ] Apply hub update.
- [ ] Apply shipment update.
- [ ] Trigger delay rescoring.
- [ ] Trigger SLA rescoring.
- [ ] Trigger hub analysis.
- [ ] Trigger decision engine.
- [ ] Trigger route reoptimization when required.
- [ ] Save event processing log.
- [ ] Add simulation state endpoint.
- [ ] Add reset endpoint.
- [ ] Add next endpoint.
- [ ] Add play endpoint.
- [ ] Add pause endpoint.
- [ ] Verify `SHP-1028` demo flow.

---

# Phase 15 — Frontend Foundation

- [ ] Create Streamlit entry point.
- [ ] Configure wide layout.
- [ ] Create centralized API client.
- [ ] Add connection timeout.
- [ ] Add non-200 error handling.
- [ ] Add invalid JSON handling.
- [ ] Add backend-unavailable state.
- [ ] Create theme constants.
- [ ] Inject shared CSS.
- [ ] Create page header component.
- [ ] Create metric card component.
- [ ] Create status badge component.
- [ ] Create environment badge.
- [ ] Create alert card component.
- [ ] Create AI provenance label.
- [ ] Create empty state component.
- [ ] Create error state component.
- [ ] Create chart helpers.
- [ ] Create map helpers.

---

# Phase 16 — Command Center Page

- [ ] Build page header.
- [ ] Show synthetic environment badge.
- [ ] Fetch analytics summary.
- [ ] Show active shipment KPI.
- [ ] Show High/Critical SLA KPI.
- [ ] Show predicted delay KPI.
- [ ] Show critical hubs KPI.
- [ ] Show CO₂ KPI.
- [ ] Show fleet utilization KPI.
- [ ] Build risk map.
- [ ] Build critical alert panel.
- [ ] Build SLA risk distribution.
- [ ] Build hub congestion heatmap.
- [ ] Build route/carbon trend.
- [ ] Build decision recommendation feed.
- [ ] Add backend-down error state.

---

# Phase 17 — Delivery Risk AI Page

- [ ] Add shipment selector.
- [ ] Show shipment context.
- [ ] Show traffic context.
- [ ] Show weather context.
- [ ] Show GPS context.
- [ ] Show hub context.
- [ ] Add loading image uploader.
- [ ] Add Run Loading Analysis button.
- [ ] Show annotated image.
- [ ] Show demo-mode warning.
- [ ] Show loading compliance score.
- [ ] Show loading warnings.
- [ ] Add Run Risk Prediction button.
- [ ] Show predicted delay.
- [ ] Show SLA probability.
- [ ] Show SLA risk badge.
- [ ] Show SLA buffer.
- [ ] Show model provenance.
- [ ] Show main factors.
- [ ] Show prediction history.
- [ ] Show generated alerts.

---

# Phase 18 — Green Route Optimizer Page

- [ ] Add shipment/batch selector.
- [ ] Add vehicle selector.
- [ ] Show capacity validation.
- [ ] Add preset selector.
- [ ] Add advanced custom weight controls.
- [ ] Validate weights.
- [ ] Add Optimize Routes button.
- [ ] Show current route.
- [ ] Show OR-Tools route.
- [ ] Show Fastest route.
- [ ] Show Greenest route.
- [ ] Show SLA Priority route.
- [ ] Show Balanced AI route.
- [ ] Build metric comparison table.
- [ ] Build route comparison chart.
- [ ] Build CO₂ comparison chart.
- [ ] Build interactive map.
- [ ] Add map candidate selector.
- [ ] Build AI recommendation panel.
- [ ] Show quantitative explanation.
- [ ] Add Save Recommendation button.
- [ ] Add reoptimization notice.

---

# Phase 19 — Network Resilience Page

- [ ] Show all-hub risk table.
- [ ] Build hub risk heatmap.
- [ ] Add hub selector.
- [ ] Show congestion score.
- [ ] Show risk badge.
- [ ] Show queue growth.
- [ ] Show dwell excess.
- [ ] Show processing utilization.
- [ ] Show likely bottleneck.
- [ ] Show evidence.
- [ ] Build queue trend.
- [ ] Build dwell trend.
- [ ] Show peak period.
- [ ] Show estimated delayed shipments.
- [ ] Add fleet utilization section.
- [ ] Show utilization score.
- [ ] Show high-use vehicles.
- [ ] Show underused vehicles.
- [ ] Show vehicle usage chart.
- [ ] Add maintenance analysis panel.
- [ ] Show operational health score.
- [ ] Show maintenance risk.
- [ ] Show check-up recommendation.
- [ ] Show rule/model provenance.

---

# Phase 20 — Live Simulation Page

- [ ] Show simulation state.
- [ ] Show simulation timestamp.
- [ ] Add Reset button.
- [ ] Add Next Event button.
- [ ] Add Auto Play button.
- [ ] Add Pause button.
- [ ] Build event stream.
- [ ] Show current shipment.
- [ ] Show current traffic.
- [ ] Show current weather.
- [ ] Show current hub state.
- [ ] Show current SLA risk.
- [ ] Show previous SLA risk.
- [ ] Show risk delta.
- [ ] Show previous route recommendation.
- [ ] Show current route recommendation.
- [ ] Show decision engine output.
- [ ] Show generated alerts.
- [ ] Ensure buttons are functional.

---

# Phase 21 — Analytics & Impact Page

- [ ] Add analysis period selection.
- [ ] Define baseline comparison.
- [ ] Show distance reduction.
- [ ] Show fuel reduction estimate.
- [ ] Show CO₂ reduction estimate.
- [ ] Show SLA risk reduction.
- [ ] Show on-time prediction change.
- [ ] Show fleet utilization.
- [ ] Build route impact chart.
- [ ] Build carbon trend.
- [ ] Build SLA trend.
- [ ] Build hub congestion trend.
- [ ] Show business assumptions.
- [ ] Show model metrics.
- [ ] Label synthetic metrics.
- [ ] Prevent fabricated percentages.

---

# Phase 22 — Data & Models Page

- [ ] Show logical data sources.
- [ ] Show source type.
- [ ] Show synthetic/real status.
- [ ] Show row/event counts.
- [ ] Show latest update time.
- [ ] Show model registry.
- [ ] Show model version.
- [ ] Show model type.
- [ ] Show training rows.
- [ ] Show metrics.
- [ ] Show model availability.
- [ ] Show fallback state.
- [ ] Show known limitations.

---

# Phase 23 — Reports Page

- [ ] Add report type selector.
- [ ] Add entity selector.
- [ ] Add period selector.
- [ ] Generate shipment risk summary.
- [ ] Generate route comparison summary.
- [ ] Generate hub risk summary.
- [ ] Generate alert summary.
- [ ] Generate executive impact summary.
- [ ] Export CSV.
- [ ] Export JSON.
- [ ] Add printable report view.
- [ ] Do not add fake PDF functionality.

---

# Phase 24 — Analytics Service

- [ ] Calculate active shipments.
- [ ] Calculate risk distribution.
- [ ] Calculate predicted delayed shipments.
- [ ] Calculate critical hub count.
- [ ] Calculate daily carbon estimate.
- [ ] Calculate fleet utilization.
- [ ] Calculate route baseline vs recommendation.
- [ ] Calculate fuel reduction.
- [ ] Calculate CO₂ reduction.
- [ ] Calculate SLA risk change.
- [ ] Calculate on-time prediction change.
- [ ] Return baseline assumptions.
- [ ] Add analytics summary endpoint.

---

# Phase 25 — Model Registry

- [ ] Define model metadata format.
- [ ] Register delay model.
- [ ] Register SLA model.
- [ ] Register carbon model.
- [ ] Register hub anomaly model if used.
- [ ] Register maintenance model if used.
- [ ] Register YOLO metrics metadata.
- [ ] Store model source.
- [ ] Store dataset type.
- [ ] Store training rows.
- [ ] Store feature names.
- [ ] Store metrics.
- [ ] Store training timestamp.
- [ ] Add models endpoint.

---

# Phase 26 — Testing

## Unit tests

- [ ] Test carbon baseline.
- [ ] Test loading compliance.
- [ ] Test delay feature engineering.
- [ ] Test SLA risk thresholds.
- [ ] Test Haversine.
- [ ] Test distance matrix.
- [ ] Test capacity validation.
- [ ] Test objective weight validation.
- [ ] Test normalization.
- [ ] Test GA chromosome.
- [ ] Test GA stop coverage.
- [ ] Test route metrics.
- [ ] Test hub feature engineering.
- [ ] Test congestion score.
- [ ] Test bottleneck detection.
- [ ] Test fleet utilization.
- [ ] Test maintenance rules.
- [ ] Test decision engine.
- [ ] Test alert deduplication.
- [ ] Test simulation event application.

## API tests

- [ ] Test `/health`.
- [ ] Test vehicle list.
- [ ] Test shipment list.
- [ ] Test hub list.
- [ ] Test risk prediction.
- [ ] Test route optimization.
- [ ] Test hub analysis.
- [ ] Test alerts.
- [ ] Test simulation reset.
- [ ] Test simulation next.
- [ ] Test analytics summary.

## Failure-mode tests

- [ ] Backend unavailable.
- [ ] Empty database.
- [ ] Missing YOLO model.
- [ ] Missing delay model.
- [ ] Missing SLA model.
- [ ] Missing carbon model.
- [ ] Corrupt image.
- [ ] Oversized image.
- [ ] Invalid coordinates.
- [ ] Negative weight.
- [ ] Vehicle overcapacity.
- [ ] Invalid route weights.
- [ ] GA returns invalid candidate.
- [ ] OR-Tools no solution.
- [ ] Empty hub history.
- [ ] Limited vehicle history.
- [ ] Database write failure.
- [ ] Malformed simulation event.

---

# Phase 27 — End-to-End Verification

- [ ] Initialize database from clean state.
- [ ] Generate demo data.
- [ ] Train delay model.
- [ ] Train SLA model.
- [ ] Train carbon model.
- [ ] Train optional maintenance model.
- [ ] Run all tests.
- [ ] Fix all test failures.
- [ ] Import FastAPI app.
- [ ] Verify `/health`.
- [ ] Start FastAPI.
- [ ] Start Streamlit.
- [ ] Open every frontend page.
- [ ] Verify every button.
- [ ] Run `SHP-1028` demo scenario.
- [ ] Verify traffic event changes risk.
- [ ] Verify hub event changes congestion.
- [ ] Verify decision engine creates alert.
- [ ] Verify route recommendation can change.
- [ ] Verify carbon comparison displays.
- [ ] Verify analytics update.
- [ ] Verify report export.
- [ ] Verify Demo Detection Mode.
- [ ] Verify no raw traceback is shown in UI.

---

# Phase 28 — Documentation and Submission Readiness

- [ ] Update README.
- [ ] Add exact installation commands.
- [ ] Add exact initialization command.
- [ ] Add exact training commands.
- [ ] Add backend run command.
- [ ] Add frontend run command.
- [ ] Add test command.
- [ ] Document dataset formats.
- [ ] Document synthetic data.
- [ ] Document model limitations.
- [ ] Document carbon assumptions.
- [ ] Document route objective weights.
- [ ] Document simulation workflow.
- [ ] Add architecture diagram.
- [ ] Add system workflow diagram.
- [ ] Add screenshots.
- [ ] Prepare 2–3 minute demo script.
- [ ] Prepare executive summary.
- [ ] Prepare business impact explanation.
- [ ] Prepare judge Q&A on synthetic data.
- [ ] Prepare judge Q&A on near-real-time simulation.
- [ ] Prepare judge Q&A on carbon methodology.
- [ ] Prepare judge Q&A on route trade-offs.
- [ ] Prepare judge Q&A on why maintenance is secondary.
