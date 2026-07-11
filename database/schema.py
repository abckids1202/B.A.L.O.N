SCHEMA_SQL = '''
CREATE TABLE IF NOT EXISTS vehicles (
  vehicle_id TEXT PRIMARY KEY, vehicle_type TEXT NOT NULL, capacity_weight_kg REAL NOT NULL,
  capacity_volume_liter REAL NOT NULL, fuel_type TEXT NOT NULL, fuel_efficiency_km_per_liter REAL NOT NULL,
  status TEXT NOT NULL, current_km REAL DEFAULT 0, last_service_km REAL DEFAULT 0,
  last_service_date TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS hubs (
  hub_id TEXT PRIMARY KEY, name TEXT NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL,
  normal_dwell_time_min REAL NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS drivers (
  driver_id TEXT PRIMARY KEY, driver_name TEXT NOT NULL, home_zone TEXT NOT NULL,
  license_class TEXT NOT NULL, assigned_vehicle_id TEXT, shift_start TEXT, shift_end TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS shipments (
  shipment_id TEXT PRIMARY KEY, origin_hub TEXT NOT NULL, destination_zone TEXT NOT NULL,
  vehicle_id TEXT, load_weight_kg REAL NOT NULL, load_volume_liter REAL NOT NULL, priority TEXT NOT NULL,
  package_category TEXT NOT NULL, planned_travel_time_min REAL NOT NULL, historical_travel_time_min REAL NOT NULL,
  route_distance_km REAL NOT NULL, sla_deadline TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Active',
  loading_compliance_score REAL DEFAULT 86, is_synthetic INTEGER DEFAULT 1,
  FOREIGN KEY(origin_hub) REFERENCES hubs(hub_id), FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id)
);
CREATE TABLE IF NOT EXISTS routes (
  route_id TEXT PRIMARY KEY, shipment_id TEXT NOT NULL, route_name TEXT NOT NULL,
  sequence_json TEXT NOT NULL, coordinates_json TEXT NOT NULL, is_current INTEGER DEFAULT 0,
  FOREIGN KEY(shipment_id) REFERENCES shipments(shipment_id)
);
CREATE TABLE IF NOT EXISTS route_candidates (
  candidate_id TEXT PRIMARY KEY, shipment_id TEXT NOT NULL, candidate_name TEXT NOT NULL,
  metrics_json TEXT NOT NULL, sequence_json TEXT NOT NULL, coordinates_json TEXT NOT NULL,
  score_history_json TEXT DEFAULT '[]', selected INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS traffic_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT, route_id TEXT, shipment_id TEXT, traffic_index REAL NOT NULL,
  average_speed_kmh REAL NOT NULL, travel_time_multiplier REAL NOT NULL, captured_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS weather_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT, shipment_id TEXT, condition TEXT NOT NULL, rainfall_mm REAL NOT NULL,
  temperature_c REAL NOT NULL, severity_index REAL NOT NULL, captured_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gps_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, shipment_id TEXT, vehicle_id TEXT, lat REAL, lon REAL,
  speed_kmh REAL, route_deviation_count INTEGER DEFAULT 0, captured_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hub_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, hub_id TEXT, shipment_id TEXT, arrival_rate_per_hour REAL,
  departure_rate_per_hour REAL, queue_size INTEGER, average_dwell_time_min REAL,
  processing_rate_per_hour REAL, sorting_time_min REAL, loading_time_min REAL, unloading_time_min REAL,
  workforce_capacity_index REAL, current_delayed_shipments INTEGER, current_total_shipments INTEGER,
  captured_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS loading_inspections (
  inspection_id TEXT PRIMARY KEY, shipment_id TEXT, compliance_score REAL, status TEXT,
  warnings_json TEXT, detections_json TEXT, image_hash TEXT, model_source TEXT, is_demo INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS operational_signals (
  signal_id TEXT PRIMARY KEY, signal_type TEXT NOT NULL, source_module TEXT NOT NULL,
  entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, shipment_id TEXT, hub_id TEXT,
  severity TEXT NOT NULL, confidence REAL NOT NULL, status TEXT NOT NULL,
  normalized_payload_json TEXT NOT NULL, state_change_json TEXT NOT NULL,
  model_source TEXT NOT NULL, is_demo INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS hub_overflow_forecasts (
  forecast_id TEXT PRIMARY KEY, hub_id TEXT NOT NULL, horizon_minutes INTEGER NOT NULL,
  overflow_probability REAL NOT NULL, expected_queue_size INTEGER NOT NULL,
  risk_level TEXT NOT NULL, evidence_json TEXT NOT NULL, model_source TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS delay_predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, shipment_id TEXT, predicted_delay_minutes REAL,
  model_source TEXT, model_version TEXT, factors_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sla_predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, shipment_id TEXT, probability REAL, risk_level TEXT,
  model_source TEXT, model_version TEXT, factors_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS carbon_estimates (
  id INTEGER PRIMARY KEY AUTOINCREMENT, shipment_id TEXT, route_name TEXT, fuel_liter REAL,
  co2_kg REAL, source TEXT, assumptions_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS route_recommendations (
  id INTEGER PRIMARY KEY AUTOINCREMENT, shipment_id TEXT, recommended_candidate TEXT, explanation TEXT,
  evidence_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS operational_interventions (
  intervention_id TEXT PRIMARY KEY, shipment_id TEXT, journey_id TEXT, journey_leg_id TEXT,
  hub_id TEXT, vehicle_id TEXT, intervention_type TEXT NOT NULL, trigger_type TEXT,
  trigger_event_id TEXT, severity TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  expires_at TEXT, status TEXT NOT NULL, recommended_action TEXT NOT NULL,
  recommended_entity_id TEXT, reason TEXT, primary_factor TEXT, evidence_json TEXT,
  before_state_json TEXT, expected_after_state_json TEXT, actual_after_state_json TEXT,
  decision_policy TEXT, accepted_at TEXT, executed_at TEXT, completed_at TEXT,
  rejected_at TEXT, rejection_reason TEXT, impact_json TEXT, is_simulated INTEGER DEFAULT 1,
  scenario_id TEXT
);
CREATE TABLE IF NOT EXISTS intervention_impacts (
  impact_id TEXT PRIMARY KEY, intervention_id TEXT NOT NULL, shipment_id TEXT,
  expected_delay_change_min REAL, actual_reforecast_delay_change_min REAL,
  expected_sla_change_pp REAL, actual_reforecast_sla_change_pp REAL,
  expected_co2_change_kg REAL, actual_reforecast_co2_change_kg REAL,
  status TEXT NOT NULL, evidence_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(intervention_id) REFERENCES operational_interventions(intervention_id)
);
CREATE TABLE IF NOT EXISTS alerts (
  alert_id TEXT PRIMARY KEY, alert_type TEXT, entity_type TEXT, entity_id TEXT, severity TEXT,
  title TEXT, message TEXT, recommendation TEXT, evidence_json TEXT, status TEXT DEFAULT 'Active',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP, acknowledged_at TEXT
);
CREATE TABLE IF NOT EXISTS maintenance_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id TEXT, event_date TEXT, event_type TEXT,
  odometer_km REAL, notes TEXT
);
CREATE TABLE IF NOT EXISTS breakdown_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id TEXT, event_date TEXT, downtime_hours REAL, notes TEXT
);
CREATE TABLE IF NOT EXISTS maintenance_predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id TEXT, health_score REAL, risk_level TEXT,
  recommended_checkup_days INTEGER, source TEXT, factors_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS model_registry (
  name TEXT PRIMARY KEY, version TEXT, model_type TEXT, file_path TEXT, dataset_type TEXT,
  training_rows INTEGER, feature_names_json TEXT, metrics_json TEXT, availability TEXT,
  fallback_state TEXT, training_timestamp TEXT
);
CREATE TABLE IF NOT EXISTS simulation_events (
  event_id TEXT PRIMARY KEY, step INTEGER NOT NULL, timestamp TEXT NOT NULL, event_type TEXT NOT NULL,
  entity_id TEXT NOT NULL, payload_json TEXT NOT NULL, processed INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS simulation_state (
  id INTEGER PRIMARY KEY CHECK (id = 1), current_step INTEGER DEFAULT 0, status TEXT DEFAULT 'Paused',
  current_timestamp TEXT, active_shipment_id TEXT DEFAULT 'SHP-1028'
);
CREATE TABLE IF NOT EXISTS operational_clock (
  runtime_id TEXT PRIMARY KEY,
  timezone TEXT NOT NULL,
  current_demo_time TEXT NOT NULL,
  wall_clock_reference TEXT,
  status TEXT NOT NULL,
  speed_multiplier REAL NOT NULL DEFAULT 1,
  last_tick_at TEXT,
  state_version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS synthetic_network_runs (
  run_id TEXT PRIMARY KEY, preset TEXT NOT NULL, shipment_count INTEGER NOT NULL,
  hub_count INTEGER NOT NULL, vehicle_count INTEGER NOT NULL, driver_count INTEGER NOT NULL,
  routing_job_count INTEGER NOT NULL, operational_event_count INTEGER NOT NULL,
  assumptions_json TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_vehicle ON shipments(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_shipments_origin ON shipments(origin_hub);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status, severity);
CREATE INDEX IF NOT EXISTS idx_sim_events_step ON simulation_events(step, processed);
CREATE INDEX IF NOT EXISTS idx_interventions_status ON operational_interventions(status, severity, created_at);
CREATE INDEX IF NOT EXISTS idx_interventions_shipment ON operational_interventions(shipment_id, intervention_type);
CREATE INDEX IF NOT EXISTS idx_operational_signals_entity ON operational_signals(entity_type, entity_id, created_at);
CREATE INDEX IF NOT EXISTS idx_operational_signals_shipment ON operational_signals(shipment_id, signal_type, created_at);
CREATE INDEX IF NOT EXISTS idx_operational_signals_hub ON operational_signals(hub_id, signal_type, created_at);

CREATE TABLE IF NOT EXISTS cv_observations (
  event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, module TEXT NOT NULL,
  source TEXT NOT NULL, camera_id TEXT, observed_at TEXT NOT NULL, demo_time TEXT,
  shipment_id TEXT, package_id TEXT, hub_id TEXT, vehicle_id TEXT,
  confidence REAL NOT NULL, severity TEXT NOT NULL, model_name TEXT,
  model_version TEXT, processing_time_ms REAL, payload_json TEXT NOT NULL,
  operational_signal_id TEXT, processing_status TEXT NOT NULL,
  duplicate_count INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS cv_runtime_sessions (
  session_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT,
  source_type TEXT, camera_id TEXT, active_mode TEXT, model_versions_json TEXT,
  demo_mode INTEGER DEFAULT 1, worker_version TEXT, events_emitted INTEGER DEFAULT 0,
  frames_processed INTEGER DEFAULT 0, average_inference_ms REAL DEFAULT 0,
  status TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cv_observations_type ON cv_observations(event_type, observed_at);
CREATE INDEX IF NOT EXISTS idx_cv_observations_entity ON cv_observations(shipment_id, hub_id, vehicle_id, observed_at);
'''
