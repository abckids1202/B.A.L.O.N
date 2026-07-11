from __future__ import annotations

import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
if ROOT.name == 'cv':
    ROOT = ROOT.parent
ROOT = ROOT.parent if ROOT.name == 'scripts' else ROOT
sys.path.insert(0, str(ROOT))
from datetime import datetime

from database.connection import initialize_database
from database import repositories as repo


HERO_PACKAGES = [
    {
        "shipment_id": "SHP-DMG-001",
        "package_id": "PKG-DMG-001",
        "priority": "EXPRESS",
        "origin_hub": "HUB-JKT",
        "destination_hub": "HUB-BKS",
        "destination_zone": "Bekasi",
        "planned_vehicle_id": "VAN-021",
        "planned_route_id": "RTE-JKT-BKS-01",
        "routing_job_id": "JOB-JKT-BKS-01",
        "sla_deadline": "2026-07-11T16:00:00+07:00",
        "current_stage": "POST_UNLOADING",
        "dispatch_ready": False,
        "demo_module": "PACKAGE_QUALITY",
    },
    {
        "shipment_id": "SHP-LOAD-001",
        "package_id": "PKG-LOAD-001",
        "priority": "EXPRESS",
        "origin_hub": "HUB-JKT",
        "destination_hub": "HUB-BKS",
        "destination_zone": "Bekasi",
        "planned_vehicle_id": "VAN-021",
        "planned_route_id": "RTE-JKT-BKS-01",
        "routing_job_id": "JOB-JKT-BKS-01",
        "sla_deadline": "2026-07-11T17:00:00+07:00",
        "current_stage": "PRE_LOADING",
        "dispatch_ready": True,
        "demo_module": "DISPATCH_VALIDATION",
    },
    {
        "shipment_id": "SHP-LOAD-002",
        "package_id": "PKG-LOAD-002",
        "priority": "REGULAR",
        "origin_hub": "HUB-JKT",
        "destination_hub": "HUB-TNG",
        "destination_zone": "Tangerang",
        "planned_vehicle_id": "VAN-044",
        "planned_route_id": "RTE-JKT-TNG-01",
        "routing_job_id": "JOB-JKT-TNG-01",
        "sla_deadline": "2026-07-11T18:30:00+07:00",
        "current_stage": "PRE_LOADING",
        "dispatch_ready": True,
        "demo_module": "LOADING_COMPLIANCE",
    },
    {
        "shipment_id": "SHP-HUB-001",
        "package_id": "PKG-HUB-001",
        "priority": "EXPRESS",
        "origin_hub": "HUB-JKT",
        "destination_hub": "HUB-BKS",
        "destination_zone": "Bekasi",
        "planned_vehicle_id": "VAN-021",
        "planned_route_id": "RTE-JKT-BKS-01",
        "routing_job_id": "JOB-JKT-BKS-01",
        "sla_deadline": "2026-07-11T19:00:00+07:00",
        "current_stage": "HUB_SORTING",
        "dispatch_ready": False,
        "demo_module": "HUB_VISION",
    },
]

LOADING_CONTEXTS = [
    {
        "loading_context_id": "CTX-JKT-BAY-02",
        "hub_id": "HUB-JKT",
        "loading_bay_id": "BAY-02",
        "current_vehicle_id": "VAN-044",
        "current_route_id": "RTE-JKT-TNG-01",
        "current_destination_id": "HUB-TNG",
        "routing_job_id": "JOB-JKT-TNG-01",
        "status": "ACTIVE",
        "comparison_expected": "WRONG_VEHICLE",
    },
    {
        "loading_context_id": "CTX-JKT-BAY-01",
        "hub_id": "HUB-JKT",
        "loading_bay_id": "BAY-01",
        "current_vehicle_id": "VAN-021",
        "current_route_id": "RTE-JKT-BKS-01",
        "current_destination_id": "HUB-BKS",
        "routing_job_id": "JOB-JKT-BKS-01",
        "status": "ACTIVE",
        "comparison_expected": "VALID",
    },
]


def ensure_tables() -> None:
    repo.execute(
        """
        CREATE TABLE IF NOT EXISTS cv_demo_packages (
          package_id TEXT PRIMARY KEY,
          shipment_id TEXT NOT NULL UNIQUE,
          priority TEXT NOT NULL,
          origin_hub TEXT NOT NULL,
          destination_hub TEXT NOT NULL,
          planned_vehicle_id TEXT NOT NULL,
          planned_route_id TEXT NOT NULL,
          routing_job_id TEXT,
          current_stage TEXT NOT NULL,
          dispatch_ready INTEGER DEFAULT 0,
          qr_payload_json TEXT NOT NULL,
          demo_module TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    repo.execute(
        """
        CREATE TABLE IF NOT EXISTS cv_demo_loading_contexts (
          loading_context_id TEXT PRIMARY KEY,
          hub_id TEXT NOT NULL,
          loading_bay_id TEXT NOT NULL,
          current_vehicle_id TEXT NOT NULL,
          current_route_id TEXT NOT NULL,
          current_destination_id TEXT NOT NULL,
          routing_job_id TEXT,
          status TEXT NOT NULL,
          comparison_expected TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    repo.execute(
        """
        CREATE TABLE IF NOT EXISTS cv_demo_loading_assignments (
          assignment_id TEXT PRIMARY KEY,
          shipment_id TEXT NOT NULL,
          package_id TEXT NOT NULL,
          planned_vehicle_id TEXT NOT NULL,
          planned_route_id TEXT NOT NULL,
          routing_job_id TEXT,
          status TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    repo.execute(
        """
        CREATE TABLE IF NOT EXISTS cv_demo_routing_jobs (
          routing_job_id TEXT PRIMARY KEY,
          route_id TEXT NOT NULL,
          origin_hub TEXT NOT NULL,
          destination_hub TEXT NOT NULL,
          vehicle_id TEXT NOT NULL,
          status TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )


def upsert_hubs() -> None:
    hubs = [
        ("HUB-JKT", "Jakarta Main Hub", -6.2088, 106.8456, 32),
        ("HUB-BKS", "Bekasi Hub", -6.2383, 106.9756, 28),
        ("HUB-TNG", "Tangerang Hub", -6.1783, 106.6319, 30),
    ]
    for row in hubs:
        repo.execute(
            "INSERT OR IGNORE INTO hubs(hub_id,name,lat,lon,normal_dwell_time_min) VALUES(?,?,?,?,?)",
            row,
        )


def upsert_vehicles_and_drivers() -> None:
    vehicles = [
        ("VAN-021", "van", 900, 4200, "gasoline", 11.2, "Active", 24300, 21000, "2026-06-20"),
        ("VAN-044", "van", 900, 4200, "gasoline", 10.8, "Active", 27800, 25000, "2026-06-22"),
    ]
    for row in vehicles:
        repo.execute(
            "INSERT OR IGNORE INTO vehicles(vehicle_id,vehicle_type,capacity_weight_kg,capacity_volume_liter,fuel_type,fuel_efficiency_km_per_liter,status,current_km,last_service_km,last_service_date) VALUES(?,?,?,?,?,?,?,?,?,?)",
            row,
        )
    drivers = [
        ("DRV-CV-021", "Ayu CV Demo", "Jakarta", "B1", "VAN-021", "08:00", "18:00"),
        ("DRV-CV-044", "Raka CV Demo", "Jakarta", "B1", "VAN-044", "08:00", "18:00"),
    ]
    for row in drivers:
        repo.execute(
            "INSERT OR IGNORE INTO drivers(driver_id,driver_name,home_zone,license_class,assigned_vehicle_id,shift_start,shift_end) VALUES(?,?,?,?,?,?,?)",
            row,
        )


def upsert_routes() -> None:
    routes = [
        ("RTE-JKT-BKS-01", "SHP-LOAD-001", "Jakarta to Bekasi CV Demo", ["HUB-JKT", "HUB-BKS"], "VAN-021"),
        ("RTE-JKT-TNG-01", "SHP-LOAD-002", "Jakarta to Tangerang CV Demo", ["HUB-JKT", "HUB-TNG"], "VAN-044"),
    ]
    coords = {
        "HUB-JKT": {"label": "HUB-JKT", "lat": -6.2088, "lon": 106.8456},
        "HUB-BKS": {"label": "HUB-BKS", "lat": -6.2383, "lon": 106.9756},
        "HUB-TNG": {"label": "HUB-TNG", "lat": -6.1783, "lon": 106.6319},
    }
    for route_id, shipment_id, name, sequence, vehicle_id in routes:
        route_coords = [coords[item] for item in sequence]
        repo.execute(
            "INSERT OR REPLACE INTO routes(route_id,shipment_id,route_name,sequence_json,coordinates_json,is_current) VALUES(?,?,?,?,?,1)",
            (route_id, shipment_id, name, json.dumps(sequence), json.dumps(route_coords)),
        )
        repo.execute(
            "INSERT OR REPLACE INTO cv_demo_routing_jobs(routing_job_id,route_id,origin_hub,destination_hub,vehicle_id,status,updated_at) VALUES(?,?,?,?,?,?,?)",
            (f"JOB-{route_id.replace('RTE-', '')}", route_id, sequence[0], sequence[-1], vehicle_id, "ACTIVE", datetime.now().isoformat()),
        )


def upsert_shipments_and_packages() -> None:
    now = datetime.now().isoformat()
    for item in HERO_PACKAGES:
        repo.execute(
            """
            INSERT OR REPLACE INTO shipments(
              shipment_id,origin_hub,destination_zone,vehicle_id,load_weight_kg,load_volume_liter,
              priority,package_category,planned_travel_time_min,historical_travel_time_min,
              route_distance_km,sla_deadline,status,loading_compliance_score,is_synthetic
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
            """,
            (
                item["shipment_id"],
                item["origin_hub"],
                item["destination_zone"],
                item["planned_vehicle_id"],
                4.5,
                18.0,
                item["priority"].title(),
                "CV Demo Parcel",
                75,
                82,
                42.0,
                item["sla_deadline"],
                "Active",
                92,
            ),
        )
        payload = {"shipment_id": item["shipment_id"], "package_id": item["package_id"], "version": 1}
        repo.execute(
            """
            INSERT OR REPLACE INTO cv_demo_packages(
              package_id,shipment_id,priority,origin_hub,destination_hub,planned_vehicle_id,
              planned_route_id,routing_job_id,current_stage,dispatch_ready,qr_payload_json,demo_module,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                item["package_id"],
                item["shipment_id"],
                item["priority"],
                item["origin_hub"],
                item["destination_hub"],
                item["planned_vehicle_id"],
                item["planned_route_id"],
                item["routing_job_id"],
                item["current_stage"],
                1 if item["dispatch_ready"] else 0,
                json.dumps(payload, separators=(",", ":")),
                item["demo_module"],
                now,
            ),
        )
        repo.execute(
            "INSERT OR REPLACE INTO cv_demo_loading_assignments(assignment_id,shipment_id,package_id,planned_vehicle_id,planned_route_id,routing_job_id,status,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (
                f"ASN-{item['package_id']}",
                item["shipment_id"],
                item["package_id"],
                item["planned_vehicle_id"],
                item["planned_route_id"],
                item["routing_job_id"],
                "PLANNED",
                now,
            ),
        )


def upsert_contexts() -> None:
    now = datetime.now().isoformat()
    for item in LOADING_CONTEXTS:
        repo.execute(
            "INSERT OR REPLACE INTO cv_demo_loading_contexts(loading_context_id,hub_id,loading_bay_id,current_vehicle_id,current_route_id,current_destination_id,routing_job_id,status,comparison_expected,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                item["loading_context_id"],
                item["hub_id"],
                item["loading_bay_id"],
                item["current_vehicle_id"],
                item["current_route_id"],
                item["current_destination_id"],
                item["routing_job_id"],
                item["status"],
                item["comparison_expected"],
                now,
            ),
        )


def main() -> None:
    initialize_database()
    ensure_tables()
    upsert_hubs()
    upsert_vehicles_and_drivers()
    upsert_shipments_and_packages()
    upsert_routes()
    upsert_contexts()
    print("Seeded CV demo packages:")
    for row in repo.rows("SELECT shipment_id, package_id, planned_vehicle_id, planned_route_id, current_stage FROM cv_demo_packages ORDER BY shipment_id"):
        print(f"- {row['shipment_id']} / {row['package_id']} -> {row['planned_vehicle_id']} / {row['planned_route_id']} / {row['current_stage']}")
    print("Seeded loading contexts:")
    for row in repo.rows("SELECT loading_context_id, current_vehicle_id, current_route_id, comparison_expected FROM cv_demo_loading_contexts ORDER BY loading_context_id"):
        print(f"- {row['loading_context_id']} -> {row['current_vehicle_id']} / {row['current_route_id']} / {row['comparison_expected']}")


if __name__ == "__main__":
    main()
