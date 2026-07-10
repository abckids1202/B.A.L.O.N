from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from database.connection import initialize_database
from database import repositories as repo


PRESETS = {
    "COMPACT_PRESENTATION": {"shipments": 500, "hubs": 12, "vehicles": 60, "drivers": 50, "routing_jobs": 40, "events": 2400},
    "LARGE_DEMO_NETWORK": {"shipments": 5000, "hubs": 30, "vehicles": 200, "drivers": 160, "routing_jobs": 250, "events": 25000},
    "STRESS_DEVELOPMENT": {"shipments": 25000, "hubs": 50, "vehicles": 500, "drivers": 400, "routing_jobs": 1000, "events": 100000},
}

BASE_TIME = datetime(2026, 7, 10, 8, 0, tzinfo=timezone(timedelta(hours=7)))
DESTINATIONS = [
    ("Bekasi Timur", -6.2477, 107.0188), ("Rawalumbu", -6.2791, 107.0021),
    ("Tambun", -6.2572, 107.0667), ("Kemang", -6.2615, 106.8117),
    ("Depok", -6.4025, 106.7942), ("BSD", -6.3024, 106.6527),
    ("Cengkareng", -6.1547, 106.7272), ("Kelapa Gading", -6.1588, 106.9059),
    ("Cibubur", -6.3562, 106.8879), ("Tangerang Kota", -6.1783, 106.6319),
]

HUB_CATALOG = [
    ("HUB-BKS", "Bekasi Cross-Dock", -6.2383, 106.9756, 35),
    ("HUB-JKT", "Jakarta Central Hub", -6.2088, 106.8456, 32),
    ("HUB-TNG", "Tangerang Hub", -6.1783, 106.6319, 30),
    ("HUB-DPK", "Depok Local Hub", -6.4025, 106.7942, 34),
    ("HUB-BSD", "BSD South Hub", -6.3024, 106.6527, 33),
    ("HUB-CGK", "Cengkareng Gateway", -6.1547, 106.7272, 38),
    ("HUB-KLG", "Kelapa Gading Sort Center", -6.1588, 106.9059, 31),
    ("HUB-CBR", "Cibubur Staging Hub", -6.3562, 106.8879, 36),
    ("FC-JKT", "Jakarta Fulfillment Center", -6.1854, 106.8330, 24),
    ("FC-BKS", "Bekasi Fulfillment Node", -6.2501, 107.0045, 25),
    ("LM-BKS", "Bekasi Last Mile Depot", -6.2477, 107.0188, 18),
    ("LM-JKT", "Jakarta Last Mile Depot", -6.2146, 106.8451, 18),
    ("HUB-BOG", "Bogor Relay Hub", -6.5971, 106.8060, 37),
    ("HUB-KRW", "Karawang Linehaul Hub", -6.3054, 107.3000, 40),
    ("LM-TNG", "Tangerang Last Mile Depot", -6.1714, 106.6403, 18),
]

VEHICLE_TYPES = {
    "motorcycle": (90, 220, "gasoline", 38.0),
    "van": (900, 4200, "diesel", 10.8),
    "electric_van": (750, 3600, "electric", 18.0),
    "box_truck": (2200, 9800, "diesel", 7.2),
}


def iso(minutes: int = 0) -> str:
    return (BASE_TIME + timedelta(minutes=minutes)).isoformat()


def haversine_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    radius = 6371
    dlat = math.radians(b_lat - a_lat)
    dlon = math.radians(b_lon - a_lon)
    x = math.sin(dlat / 2) ** 2 + math.cos(math.radians(a_lat)) * math.cos(math.radians(b_lat)) * math.sin(dlon / 2) ** 2
    return round(radius * 2 * math.atan2(math.sqrt(x), math.sqrt(1 - x)), 2)


def clear_tables() -> None:
    for table in [
        "intervention_impacts", "operational_interventions", "hub_overflow_forecasts", "operational_signals",
        "route_candidates", "routes", "traffic_snapshots", "weather_snapshots", "gps_events", "hub_events",
        "loading_inspections", "delay_predictions", "sla_predictions", "carbon_estimates", "route_recommendations",
        "alerts", "maintenance_history", "breakdown_history", "maintenance_predictions", "simulation_events",
        "simulation_state", "operational_clock", "shipments", "drivers", "vehicles", "hubs", "model_registry", "synthetic_network_runs",
    ]:
        repo.execute(f"DELETE FROM {table}")


def vehicle_id_for(index: int, vehicle_type: str) -> str:
    prefix = {"motorcycle": "MTR", "van": "VAN", "electric_van": "EV", "box_truck": "TRK"}[vehicle_type]
    return f"{prefix}-{index:03d}"


def build_route(origin: tuple, destination: tuple, index: int) -> list[dict]:
    dest_name, dest_lat, dest_lon = destination
    return [
        {"stop_id": origin[0], "label": origin[1], "lat": origin[2], "lon": origin[3], "risk_hint": 0.2 + (index % 7) * 0.04},
        {"stop_id": "GATEWAY-JKT", "label": "Jakarta Gateway", "lat": -6.2146, "lon": 106.8451, "risk_hint": 0.36 + (index % 5) * 0.06},
        {"stop_id": f"ZONE-{dest_name.upper().replace(' ', '-')}", "label": dest_name, "lat": dest_lat, "lon": dest_lon, "risk_hint": 0.28 + (index % 9) * 0.05},
    ]


def main(preset: str = "COMPACT_PRESENTATION") -> None:
    preset = preset.upper()
    cfg = PRESETS.get(preset, PRESETS["COMPACT_PRESENTATION"])
    rng = random.Random(42)
    initialize_database()
    clear_tables()

    hubs = HUB_CATALOG[: cfg["hubs"]]
    repo.execute_many("INSERT INTO hubs VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)", hubs)

    vehicle_rows = []
    for i in range(cfg["vehicles"]):
        if i % 11 == 0:
            vtype = "box_truck"
        elif i % 5 == 0:
            vtype = "electric_van"
        elif i % 3 == 0:
            vtype = "motorcycle"
        else:
            vtype = "van"
        cap_w, cap_v, fuel, eff = VEHICLE_TYPES[vtype]
        status = "Maintenance" if i % 29 == 0 else ("Idle" if i % 7 == 0 else "Active")
        vehicle_rows.append((vehicle_id_for(i + 1, vtype), vtype, cap_w, cap_v, fuel, eff, status, 9000 + i * 417, 7600 + i * 389, "2026-06-15"))
    repo.execute_many("INSERT INTO vehicles VALUES(?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)", vehicle_rows)
    assignable_vehicle_rows = [row for row in vehicle_rows if row[6] == "Active"]

    driver_rows = []
    names = ["Raka", "Dimas", "Maya", "Andi", "Sari", "Bima", "Nadia", "Fajar", "Intan", "Rizky"]
    for i in range(cfg["drivers"]):
        vehicle = vehicle_rows[i % len(vehicle_rows)][0]
        driver_rows.append((f"DRV-{i+1:03d}", f"{names[i % len(names)]} {['Pratama','Wijaya','Putra','Sari','Halim'][i % 5]}", hubs[i % len(hubs)][0], "A" if i % 3 == 0 else "B1", vehicle, "08:00", "17:00"))
    repo.execute_many("INSERT INTO drivers(driver_id,driver_name,home_zone,license_class,assigned_vehicle_id,shift_start,shift_end) VALUES(?,?,?,?,?,?,?)", driver_rows)

    shipments = []
    route_rows = []
    traffic_rows = []
    weather_rows = []
    gps_rows = []
    hub_event_rows = []
    carbon_rows = []
    route_recommendation_rows = []
    priorities = ["Standard", "Standard", "Express", "Standard", "Critical"]
    categories = ["mixed_parcels", "electronics", "home_goods", "fashion", "grocery", "documents"]

    hero_vehicle = "VAN-002" if any(v[0] == "VAN-002" for v in vehicle_rows) else vehicle_rows[1][0]
    for i in range(cfg["shipments"]):
        is_hero = i == 0
        shipment_id = "SHP-1028" if is_hero else f"SHP-{2000 + i:05d}"
        origin = hubs[(i * 5 + 2) % len(hubs)]
        destination = DESTINATIONS[(i * 7 + 3) % len(DESTINATIONS)]
        vehicle = hero_vehicle if is_hero else assignable_vehicle_rows[(i * 13 + 4) % len(assignable_vehicle_rows)][0]
        vtype = next(v[1] for v in vehicle_rows if v[0] == vehicle)
        base_weight = {"motorcycle": 12, "van": 180, "electric_van": 150, "box_truck": 520}[vtype]
        load_weight = round(base_weight + (i % 17) * (4.5 if vtype == "motorcycle" else 23.5), 1)
        load_volume = round(load_weight * (3.2 + (i % 5) * 0.34), 1)
        distance = haversine_km(origin[2], origin[3], destination[1], destination[2]) + 8 + (i % 9) * 1.7
        traffic_index = round(min(0.92, 0.18 + ((i * 37) % 71) / 100), 3)
        rain = round(((i * 19) % 28) * 0.8, 1)
        weather_severity = round(min(0.86, rain / 30), 3)
        hub_dwell = round(origin[4] + ((i * 11) % 52) * 0.9 + (14 if i % 23 == 0 else 0), 1)
        planned = round(28 + distance * (2.1 if vtype == "motorcycle" else 1.55) + origin[4] * 0.55, 1)
        historical = round(planned + traffic_index * 24 + max(0, hub_dwell - origin[4]) * 0.42 + weather_severity * 18, 1)
        priority = "Express" if is_hero else priorities[(i * 7) % len(priorities)]
        category = categories[(i * 3 + 1) % len(categories)]
        status = "Delivered" if i % 19 == 0 and not is_hero else "Active"
        compliance = round(max(62, 95 - (i % 21) * 0.9 - (6 if category == "electronics" else 0)), 1)
        created_offset = (i * 7) % 150
        sla_deadline = iso(created_offset + int(planned + 80 + (i % 11) * 9))
        shipments.append((shipment_id, origin[0], destination[0], vehicle, load_weight, load_volume, priority, category, planned, historical, round(distance, 2), sla_deadline, status, compliance, 1))

        stops = build_route(origin, destination, i)
        route_rows.append((f"ROUTE-{shipment_id}", shipment_id, "Current Route", json.dumps([s["stop_id"] for s in stops]), json.dumps(stops), 1))
        traffic_rows.append((f"ROUTE-{shipment_id}", shipment_id, traffic_index, round(max(12, 42 * (1 - traffic_index * 0.48)), 1), round(1 + traffic_index, 3), iso(created_offset)))
        condition = "Heavy Rain" if rain >= 16 else ("Light Rain" if rain >= 4 else "Clear")
        weather_rows.append((shipment_id, condition, rain, round(27 + (i % 8) * 0.7, 1), weather_severity, iso(created_offset)))
        progress = ((i * 17) % 100) / 100
        lat = origin[2] + (destination[1] - origin[2]) * progress
        lon = origin[3] + (destination[2] - origin[3]) * progress
        gps_rows.append((shipment_id, vehicle, round(lat, 5), round(lon, 5), 0 if status == "Delivered" else round(max(0, 38 * (1 - traffic_index * 0.5)), 1), 1 if traffic_index > 0.78 and i % 4 == 0 else 0, iso(created_offset)))
        queue = 8 + ((i * 13) % 45)
        hub_event_rows.append((origin[0], shipment_id, 18 + (i % 30), 16 + ((i * 3) % 28), queue, hub_dwell, max(16, 38 - int(traffic_index * 12)), 18 + (i % 35), 14 + ((i * 2) % 24), 12 + ((i * 5) % 21), round(max(0.55, 1 - traffic_index * 0.34), 2), int(queue * traffic_index), 60 + (i % 80), iso(created_offset)))
        co2 = round(distance * load_weight / 1000 * (0.11 if vtype == "electric_van" else 0.42), 3)
        carbon_rows.append((shipment_id, "Current Route", round(distance / 10.8, 3), co2, "CF-DEMO-2026", json.dumps({"distance_km": round(distance, 2), "weight_kg": load_weight, "fuel_type": next(v[4] for v in vehicle_rows if v[0] == vehicle)})))
        if i < cfg["routing_jobs"]:
            route_recommendation_rows.append((shipment_id, "Balanced Detour", "Synthetic route recommendation derived from traffic, dwell, capacity, and carbon context.", json.dumps({"traffic_index": traffic_index, "hub_dwell_min": hub_dwell, "distance_km": round(distance, 2)})))

    repo.execute_many("INSERT INTO shipments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", shipments)
    repo.execute_many("INSERT INTO routes(route_id,shipment_id,route_name,sequence_json,coordinates_json,is_current) VALUES(?,?,?,?,?,?)", route_rows)
    repo.execute_many("INSERT INTO traffic_snapshots(route_id,shipment_id,traffic_index,average_speed_kmh,travel_time_multiplier,captured_at) VALUES(?,?,?,?,?,?)", traffic_rows)
    repo.execute_many("INSERT INTO weather_snapshots(shipment_id,condition,rainfall_mm,temperature_c,severity_index,captured_at) VALUES(?,?,?,?,?,?)", weather_rows)
    repo.execute_many("INSERT INTO gps_events(shipment_id,vehicle_id,lat,lon,speed_kmh,route_deviation_count,captured_at) VALUES(?,?,?,?,?,?,?)", gps_rows)
    repo.execute_many("INSERT INTO hub_events(hub_id,shipment_id,arrival_rate_per_hour,departure_rate_per_hour,queue_size,average_dwell_time_min,processing_rate_per_hour,sorting_time_min,loading_time_min,unloading_time_min,workforce_capacity_index,current_delayed_shipments,current_total_shipments,captured_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", hub_event_rows)
    repo.execute_many("INSERT INTO carbon_estimates(shipment_id,route_name,fuel_liter,co2_kg,source,assumptions_json) VALUES(?,?,?,?,?,?)", carbon_rows)
    repo.execute_many("INSERT INTO route_recommendations(shipment_id,recommended_candidate,explanation,evidence_json) VALUES(?,?,?,?)", route_recommendation_rows)

    repo.execute("INSERT INTO traffic_snapshots(route_id,shipment_id,traffic_index,average_speed_kmh,travel_time_multiplier,captured_at) VALUES(?,?,?,?,?,?)", ("ROUTE-SHP-1028", "SHP-1028", 0.55, 31.0, 1.32, iso(20)))
    repo.execute("INSERT INTO weather_snapshots(shipment_id,condition,rainfall_mm,temperature_c,severity_index,captured_at) VALUES(?,?,?,?,?,?)", ("SHP-1028", "Light Rain", 5.5, 28.2, 0.34, iso(20)))
    repo.execute("INSERT INTO gps_events(shipment_id,vehicle_id,lat,lon,speed_kmh,route_deviation_count,captured_at) VALUES(?,?,?,?,?,?,?)", ("SHP-1028", hero_vehicle, -6.2088, 106.8456, 31.0, 0, iso(20)))

    for hub_id in ["HUB-JKT", "HUB-BKS", "HUB-TNG"]:
        repo.execute("INSERT INTO hub_events(hub_id,shipment_id,arrival_rate_per_hour,departure_rate_per_hour,queue_size,average_dwell_time_min,processing_rate_per_hour,sorting_time_min,loading_time_min,unloading_time_min,workforce_capacity_index,current_delayed_shipments,current_total_shipments,captured_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (hub_id, "SHP-1028", 38, 19, 34, 83, 26, 56, 34, 29, .71, 26, 92, iso(90)))

    repo.execute("INSERT INTO breakdown_history(vehicle_id,event_date,downtime_hours,notes) VALUES(?,?,?,?)", (hero_vehicle, "2026-05-22", 4, "Cooling inspection after high load route."))
    events = [
        ("EVT-001", 1, iso(30), "ORIGIN_DISPATCHED", "FC-JKT", {"vehicle_id": hero_vehicle, "lat": -6.2088, "lon": 106.8456, "speed_kmh": 31, "route_deviation_count": 0, "description": "SHP-1028 left the fulfillment origin for the main hub."}),
        ("EVT-002", 2, iso(60), "HUB_ARRIVED", "HUB-JKT", {"hub_id": "HUB-JKT", "average_dwell_time_min": 0, "queue_size": 8, "sorting_time_min": 0, "loading_time_min": 0, "unloading_time_min": 12, "description": "SHP-1028 arrived at HUB-JKT and entered hub processing."}),
        ("EVT-003", 3, iso(90), "HUB_UPDATE", "HUB-JKT", {"hub_id": "HUB-JKT", "arrival_rate_per_hour": 38, "departure_rate_per_hour": 19, "queue_size": 34, "average_dwell_time_min": 83, "processing_rate_per_hour": 26, "sorting_time_min": 56, "loading_time_min": 34, "unloading_time_min": 29, "workforce_capacity_index": 0.71, "current_delayed_shipments": 26, "current_total_shipments": 92, "severity": "Warning", "description": "Sorting delay increased hub dwell and triggered a new risk evaluation."}),
        ("EVT-004", 4, iso(110), "HUB_DEPARTED", "HUB-JKT", {"vehicle_id": hero_vehicle, "traffic_index": 0.68, "average_speed_kmh": 24, "travel_time_multiplier": 1.45, "lat": -6.231, "lon": 106.91, "speed_kmh": 24, "description": "The package departed HUB-JKT on the inter-hub leg to HUB-BKS."}),
        ("EVT-005", 5, iso(125), "WEATHER_UPDATE", "SHP-1028", {"condition": "Heavy Rain", "rainfall_mm": 18.5, "temperature_c": 27.5, "severity_index": 0.78, "severity": "Warning", "description": "Heavy rain affected the active inter-hub transport leg."}),
        ("EVT-006", 6, iso(145), "LOCAL_HUB_ARRIVED", "HUB-BKS", {"hub_id": "HUB-BKS", "arrival_rate_per_hour": 30, "departure_rate_per_hour": 27, "queue_size": 16, "average_dwell_time_min": 37, "processing_rate_per_hour": 31, "sorting_time_min": 24, "loading_time_min": 20, "unloading_time_min": 18, "workforce_capacity_index": 0.88, "current_delayed_shipments": 8, "current_total_shipments": 84, "description": "SHP-1028 arrived at the Bekasi local hub for last-mile staging."}),
        ("EVT-007", 7, iso(160), "LAST_MILE_STARTED", "MTR-004", {"vehicle_id": "MTR-004", "lat": -6.2477, "lon": 107.0188, "speed_kmh": 26, "route_deviation_count": 0, "description": "Last-mile courier assignment started for Bekasi Timur."}),
        ("EVT-008", 8, iso(178), "DELIVERED", "BUYER", {"description": "Package was delivered to the buyer in Bekasi Timur.", "severity": "Info"}),
    ]
    repo.execute_many("INSERT INTO simulation_events(event_id,step,timestamp,event_type,entity_id,payload_json,processed) VALUES(?,?,?,?,?,?,0)", [(e[0], e[1], e[2], e[3], e[4], json.dumps(e[5])) for e in events])
    repo.execute("INSERT OR REPLACE INTO simulation_state(id,current_step,status,current_timestamp,active_shipment_id) VALUES(1,0,'Paused',?,'SHP-1028')", (iso(),))

    repo.execute("INSERT OR REPLACE INTO operational_clock(runtime_id,timezone,current_demo_time,wall_clock_reference,status,speed_multiplier,last_tick_at,state_version) VALUES(?,?,?,?,?,?,?,?)", ("DEMO-RUNTIME-20260710", "Asia/Jakarta", iso(392), None, "RUNNING", 5, iso(392), 1))

    model_rows = [
        ("PackageDamagePrototypeEngine", "v1", "prototype_visual_signal", "models/package_damage_yolo.pt", "team image dataset required", 0, json.dumps(["crushed_box", "torn_corner", "wet_label"]), json.dumps({"mode": "deterministic demo", "precision": "not trained"}), "DEMO_MODE", "YOLO artifact optional; deterministic fallback active", iso()),
        ("HubOccupancyPrototypeEngine", "v1", "prototype_visual_signal", "models/hub_occupancy_yolo.pt", "hub frame dataset required", 0, json.dumps(["package", "pallet", "worker", "occupied_zone"]), json.dumps({"mode": "density heuristic", "accuracy": "prototype"}), "DEMO_MODE", "Visual density fallback active", iso()),
        ("PrototypeHubOverflowForecastEngine", "v1", "prototype_forecast", "models/hub_overflow.pkl", "synthetic hub event stream", 0, json.dumps(["arrival_rate", "departure_rate", "queue_size", "dwell_excess"]), json.dumps({"mode": "queue growth heuristic"}), "DEMO_MODE", "Deterministic forecast fallback active", iso()),
        ("VisionLoadingValidationEngine", "v1", "prototype_validation", "models/loading_validation.pt", "dock image + shipment plan", 0, json.dumps(["planned_vehicle_id", "observed_vehicle_id", "package_scan"]), json.dumps({"mode": "plan reconciliation"}), "DEMO_MODE", "Shipment-plan validation fallback active", iso()),
    ]
    repo.execute_many("INSERT OR REPLACE INTO model_registry(name,version,model_type,file_path,dataset_type,training_rows,feature_names_json,metrics_json,availability,fallback_state,training_timestamp) VALUES(?,?,?,?,?,?,?,?,?,?,?)", model_rows)
    for i in range(24):
        sid = "SHP-1028" if i == 0 else f"SHP-{2001 + i:05d}"
        intervention_id = f"HIST-ROUTE-{i+1:03d}"
        before_distance = round(34 + (i % 9) * 3.4, 2)
        after_distance = round(before_distance - (1.2 + (i % 5) * 0.7), 2)
        is_ev_impact = i % 5 == 0
        before_fuel = 0 if is_ev_impact else round(before_distance / 10.8, 3)
        after_fuel = 0 if is_ev_impact else round(after_distance / 11.3, 3)
        before_energy = round(before_distance * 0.19, 3) if is_ev_impact else 0
        after_energy = round(after_distance * 0.17, 3) if is_ev_impact else 0
        before_co2 = round(before_energy * 0.82 if is_ev_impact else before_fuel * 2.68, 3)
        after_co2 = round(after_energy * 0.82 if is_ev_impact else after_fuel * 2.68, 3)
        before_delay = 38 + (i % 8) * 6
        after_delay = max(8, before_delay - (7 + (i % 6) * 3))
        before_sla = round(0.48 + (i % 7) * 0.055, 3)
        after_sla = round(max(0.08, before_sla - (0.11 + (i % 5) * 0.025)), 3)
        before = {"distance_km": before_distance, "fuel_liter": before_fuel, "energy_kwh": before_energy, "co2_kg": before_co2, "delay_min": before_delay, "sla_probability": before_sla}
        after = {"distance_km": after_distance, "fuel_liter": after_fuel, "energy_kwh": after_energy, "co2_kg": after_co2, "delay_min": after_delay, "sla_probability": after_sla}
        impact = {"expected_delay_change_min": round(after_delay - before_delay, 1), "actual_reforecast_delay_change_min": round(after_delay - before_delay, 1), "expected_sla_change_pp": round((after_sla - before_sla) * 100, 2), "actual_reforecast_sla_change_pp": round((after_sla - before_sla) * 100, 2), "expected_co2_change_kg": round(after_co2 - before_co2, 3), "actual_reforecast_co2_change_kg": round(after_co2 - before_co2, 3), "status": "IMPROVED", "evidence": {"before": before, "after": after, "methodology": "synthetic completed intervention replay"}}
        completed_at = iso(20 + i * 11)
        repo.execute("INSERT OR REPLACE INTO operational_interventions(intervention_id,shipment_id,journey_id,journey_leg_id,hub_id,vehicle_id,intervention_type,trigger_type,trigger_event_id,severity,status,recommended_action,recommended_entity_id,reason,primary_factor,evidence_json,before_state_json,expected_after_state_json,actual_after_state_json,decision_policy,accepted_at,executed_at,completed_at,impact_json,is_simulated,scenario_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (intervention_id, sid, f"JRN-{sid}", None, None, None, "ROUTE_REOPTIMIZATION", "HISTORICAL_TRAFFIC_PRESSURE", f"HIST-EVT-{i+1:03d}", "High" if before_sla > .7 else "Warning", "COMPLETED", "Apply lower-risk route candidate.", "Balanced AI", "Historical route intervention reduced time, carbon, and SLA exposure.", "Traffic pressure and SLA buffer changed materially.", json.dumps({"before": before, "after": after}), json.dumps(before), json.dumps(after), json.dumps(after), "AUTOMATED_DEMO_POLICY_V1", completed_at, completed_at, completed_at, json.dumps(impact), 1, "COMPACT_HISTORY"))
        repo.execute("INSERT OR REPLACE INTO intervention_impacts(impact_id,intervention_id,shipment_id,expected_delay_change_min,actual_reforecast_delay_change_min,expected_sla_change_pp,actual_reforecast_sla_change_pp,expected_co2_change_kg,actual_reforecast_co2_change_kg,status,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (f"IMP-{intervention_id}", intervention_id, sid, impact["expected_delay_change_min"], impact["actual_reforecast_delay_change_min"], impact["expected_sla_change_pp"], impact["actual_reforecast_sla_change_pp"], impact["expected_co2_change_kg"], impact["actual_reforecast_co2_change_kg"], "IMPROVED", json.dumps(impact["evidence"])))

    assumptions = {"preset": preset, "deterministic_seed": 42, "geography": "Synthetic Jabodetabek logistics network", "event_count_note": "Operational events are represented by traffic, weather, GPS, hub, route, signal, and hero simulation records."}
    repo.execute("INSERT INTO synthetic_network_runs(run_id,preset,shipment_count,hub_count,vehicle_count,driver_count,routing_job_count,operational_event_count,assumptions_json) VALUES(?,?,?,?,?,?,?,?,?)", ("RUN-COMPACT-20260705", preset, cfg["shipments"], cfg["hubs"], cfg["vehicles"], cfg["drivers"], cfg["routing_jobs"], cfg["events"], json.dumps(assumptions)))
    Path("data/demo/demo_manifest.json").write_text(json.dumps({"synthetic": True, "scenario": "SHP-1028", "preset": preset, **cfg}, indent=2), encoding="utf-8")
    print(f"Generated {preset} synthetic network: {cfg['shipments']} shipments, {cfg['hubs']} nodes, {cfg['vehicles']} vehicles, {cfg['drivers']} drivers.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", default="COMPACT_PRESENTATION", choices=sorted(PRESETS))
    args = parser.parse_args()
    main(args.preset)
