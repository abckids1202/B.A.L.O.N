from __future__ import annotations


def analyze_fleet(vehicles: list[dict], shipments: list[dict]) -> dict:
    active_ids = {s["vehicle_id"] for s in shipments if s.get("vehicle_id")}
    total = max(len(vehicles), 1)
    active_ratio = len(active_ids) / total
    usage = []
    for vehicle in vehicles:
        assigned = [s for s in shipments if s.get("vehicle_id") == vehicle["vehicle_id"]]
        total_weight = sum(s["load_weight_kg"] for s in assigned)
        load_utilization = total_weight / max(vehicle["capacity_weight_kg"], 1)
        usage.append({
            "vehicle_id": vehicle["vehicle_id"],
            "shipment_count": len(assigned),
            "load_utilization": round(load_utilization, 3),
            "status": vehicle["status"],
        })
    underused = [u["vehicle_id"] for u in usage if u["shipment_count"] == 0]
    high_use = [u["vehicle_id"] for u in usage if u["load_utilization"] >= 0.75 or u["shipment_count"] >= 3]
    score = round(min(100, active_ratio * 70 + (1 - len(underused) / total) * 30), 1)
    return {
        "active_vehicle_ratio": round(active_ratio, 3),
        "fleet_utilization_score": score,
        "idle_vehicle_count": len(underused),
        "underused_vehicles": underused,
        "high_use_vehicles": high_use,
        "vehicle_usage": usage,
    }
