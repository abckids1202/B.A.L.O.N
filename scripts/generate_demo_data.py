from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from database.connection import initialize_database
from database import repositories as repo


def iso(minutes: int = 0) -> str:
    return (datetime(2026, 7, 5, 9, 0, tzinfo=timezone(timedelta(hours=7))) + timedelta(minutes=minutes)).isoformat()


def main() -> None:
    initialize_database()
    for table in ["route_candidates","routes","traffic_snapshots","weather_snapshots","gps_events","hub_events","loading_inspections","delay_predictions","sla_predictions","carbon_estimates","route_recommendations","alerts","maintenance_history","breakdown_history","maintenance_predictions","simulation_events","simulation_state","shipments","vehicles","hubs","model_registry"]:
        repo.execute(f"DELETE FROM {table}")
    vehicles = [
        ("VAN-021","van",900,4200,"diesel",10.8,"Active",38450,34200,"2026-05-15"),
        ("MTR-002","motorcycle",90,220,"gasoline",38.0,"Active",18800,15700,"2026-04-01"),
        ("VAN-044","van",1000,4600,"diesel",11.6,"Idle",22050,21400,"2026-06-15"),
        ("EV-007","electric_van",750,3600,"electric",18.0,"Active",12100,9300,"2026-03-28"),
    ]
    repo.execute_many("INSERT INTO vehicles VALUES(?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)", vehicles)
    hubs = [
        ("HUB-JKT","Jakarta Central Hub",-6.2088,106.8456,32),
        ("HUB-BKS","Bekasi Cross-Dock",-6.2383,106.9756,35),
        ("HUB-TNG","Tangerang Hub",-6.1783,106.6319,30),
    ]
    repo.execute_many("INSERT INTO hubs VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)", hubs)
    shipments = [
        ("SHP-1028","HUB-BKS","Bekasi Timur","VAN-021",520,2100,"Express","mixed_parcels",74,82,31.5,iso(165),"Active",84,1),
        ("SHP-1031","HUB-JKT","Kemang","MTR-002",42,95,"Standard","small_parcels",38,42,12.1,iso(210),"Active",91,1),
        ("SHP-1038","HUB-TNG","BSD","EV-007",410,1700,"Critical","electronics",66,70,28.0,iso(140),"Active",88,1),
        ("SHP-1044","HUB-JKT","Depok","VAN-044",610,2500,"Standard","home_goods",82,86,36.2,iso(260),"Active",79,1),
    ]
    repo.execute_many("INSERT INTO shipments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", shipments)
    stops = [
        {"stop_id":"DEPOT-HUB-BKS","label":"Bekasi Hub","lat":-6.2383,"lon":106.9756,"risk_hint":0.4},
        {"stop_id":"STOP-BKS-01","label":"Rawalumbu","lat":-6.2791,"lon":107.0021,"risk_hint":0.5},
        {"stop_id":"STOP-BKS-02","label":"Tambun","lat":-6.2572,"lon":107.0667,"risk_hint":0.7},
        {"stop_id":"STOP-BKS-03","label":"Mustika Jaya","lat":-6.3069,"lon":107.0205,"risk_hint":0.8},
        {"stop_id":"STOP-BKS-04","label":"Bekasi Timur","lat":-6.2477,"lon":107.0188,"risk_hint":0.6},
    ]
    repo.execute("INSERT INTO routes(route_id,shipment_id,route_name,sequence_json,coordinates_json,is_current) VALUES(?,?,?,?,?,1)", ("ROUTE-JKT-BKS-01","SHP-1028","Current Route",json.dumps([s["stop_id"] for s in stops]),json.dumps(stops)))
    for sid in ["SHP-1031", "SHP-1038", "SHP-1044"]:
        repo.execute("INSERT INTO routes(route_id,shipment_id,route_name,sequence_json,coordinates_json,is_current) VALUES(?,?,?,?,?,1)", (f"ROUTE-{sid}",sid,"Current Route",json.dumps([s["stop_id"] for s in stops[:3]]),json.dumps(stops[:3])))
    for sid, t, w, h in [("SHP-1028",0.48,0.12,42),("SHP-1031",0.28,0.05,28),("SHP-1038",0.61,0.20,51),("SHP-1044",0.35,0.10,33)]:
        repo.execute("INSERT INTO traffic_snapshots(route_id,shipment_id,traffic_index,average_speed_kmh,travel_time_multiplier,captured_at) VALUES(?,?,?,?,?,?)", ("ROUTE",sid,t,32*(1-t/2),1+t,iso()))
        repo.execute("INSERT INTO weather_snapshots(shipment_id,condition,rainfall_mm,temperature_c,severity_index,captured_at) VALUES(?,?,?,?,?,?)", (sid,"Clear" if w < .1 else "Light Rain",w*20,29,w,iso()))
        repo.execute("INSERT INTO gps_events(shipment_id,vehicle_id,lat,lon,speed_kmh,route_deviation_count,captured_at) VALUES(?,?,?,?,?,?,?)", (sid,"VAN-021",-6.25,106.99,31,0,iso()))
        repo.execute("INSERT INTO hub_events(hub_id,shipment_id,arrival_rate_per_hour,departure_rate_per_hour,queue_size,average_dwell_time_min,processing_rate_per_hour,sorting_time_min,loading_time_min,unloading_time_min,workforce_capacity_index,current_delayed_shipments,current_total_shipments,captured_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("HUB-BKS" if sid=="SHP-1028" else "HUB-JKT",sid,22,20,11,h,30,24,20,18,.92,4,80,iso()))
    for hub_id in ["HUB-JKT","HUB-TNG"]:
        repo.execute("INSERT INTO hub_events(hub_id,shipment_id,arrival_rate_per_hour,departure_rate_per_hour,queue_size,average_dwell_time_min,processing_rate_per_hour,sorting_time_min,loading_time_min,unloading_time_min,workforce_capacity_index,current_delayed_shipments,current_total_shipments,captured_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (hub_id,"SHP-1031",18,19,7,29,33,20,18,17,.95,2,70,iso()))
    repo.execute("INSERT INTO breakdown_history(vehicle_id,event_date,downtime_hours,notes) VALUES(?,?,?,?)", ("VAN-021","2026-05-22",4,"Cooling inspection after high load route."))
    events = [
        ("EVT-001",1,iso(30),"ORIGIN_DISPATCHED","FC-JKT",{"vehicle_id":"TRK-012","lat":-6.2088,"lon":106.8456,"speed_kmh":31,"route_deviation_count":0,"description":"SHP-1028 left the fulfillment origin for the main hub."}),
        ("EVT-002",2,iso(60),"HUB_ARRIVED","HUB-JKT",{"hub_id":"HUB-JKT","average_dwell_time_min":0,"queue_size":8,"sorting_time_min":0,"loading_time_min":0,"unloading_time_min":12,"description":"SHP-1028 arrived at HUB-JKT and entered hub processing."}),
        ("EVT-003",3,iso(90),"HUB_UPDATE","HUB-JKT",{"hub_id":"HUB-JKT","arrival_rate_per_hour":38,"departure_rate_per_hour":19,"queue_size":34,"average_dwell_time_min":83,"processing_rate_per_hour":26,"sorting_time_min":56,"loading_time_min":34,"unloading_time_min":29,"workforce_capacity_index":0.71,"current_delayed_shipments":26,"current_total_shipments":92,"severity":"Warning","description":"Sorting delay increased hub dwell and triggered a new risk evaluation."}),
        ("EVT-004",4,iso(110),"HUB_DEPARTED","HUB-JKT",{"vehicle_id":"VAN-021","traffic_index":0.68,"average_speed_kmh":24,"travel_time_multiplier":1.45,"lat":-6.231,"lon":106.91,"speed_kmh":24,"description":"The package departed HUB-JKT on the inter-hub leg to HUB-BKS."}),
        ("EVT-005",5,iso(125),"WEATHER_UPDATE","SHP-1028",{"condition":"Heavy Rain","rainfall_mm":18.5,"temperature_c":27.5,"severity_index":0.78,"severity":"Warning","description":"Heavy rain affected the active inter-hub transport leg."}),
        ("EVT-006",6,iso(145),"LOCAL_HUB_ARRIVED","HUB-BKS",{"hub_id":"HUB-BKS","arrival_rate_per_hour":30,"departure_rate_per_hour":27,"queue_size":16,"average_dwell_time_min":37,"processing_rate_per_hour":31,"sorting_time_min":24,"loading_time_min":20,"unloading_time_min":18,"workforce_capacity_index":0.88,"current_delayed_shipments":8,"current_total_shipments":84,"description":"SHP-1028 arrived at the Bekasi local hub for last-mile staging."}),
        ("EVT-007",7,iso(160),"LAST_MILE_STARTED","MTR-002",{"vehicle_id":"MTR-002","lat":-6.2477,"lon":107.0188,"speed_kmh":26,"route_deviation_count":0,"description":"Last-mile courier assignment started for Bekasi Timur."}),
        ("EVT-008",8,iso(178),"DELIVERED","BUYER",{"description":"Package was delivered to the buyer in Bekasi Timur.","severity":"Info"}),
    ]
    repo.execute_many("INSERT INTO simulation_events(event_id,step,timestamp,event_type,entity_id,payload_json,processed) VALUES(?,?,?,?,?,?,0)", [(e[0],e[1],e[2],e[3],e[4],json.dumps(e[5])) for e in events])
    repo.execute("INSERT OR REPLACE INTO simulation_state(id,current_step,status,current_timestamp,active_shipment_id) VALUES(1,0,'Paused',?,'SHP-1028')", (iso(),))
    Path("data/demo/demo_manifest.json").write_text(json.dumps({"synthetic": True, "scenario": "SHP-1028"}, indent=2), encoding="utf-8")
    print("Generated synthetic demo data.")


if __name__ == "__main__":
    main()
