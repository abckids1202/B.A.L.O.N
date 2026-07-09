from __future__ import annotations


def analyze_fleet(vehicles: list[dict], shipments: list[dict]) -> dict:
    active_ids = {s["vehicle_id"] for s in shipments if s.get("vehicle_id") and s.get("status") == "Active"}
    total = len(vehicles)
    total_safe = max(total, 1)
    active_count = len(active_ids)
    idle_count = len([v for v in vehicles if v["vehicle_id"] not in active_ids and v.get("status") == "Idle"])
    maintenance_count = len([v for v in vehicles if str(v.get("status", "")).lower() == "maintenance"])
    unavailable_count = len([v for v in vehicles if str(v.get("status", "")).lower() in {"unavailable", "offline"}])
    usage = []
    for index, vehicle in enumerate(vehicles):
        assigned = [s for s in shipments if s.get("vehicle_id") == vehicle["vehicle_id"] and s.get("status") == "Active"]
        total_weight = sum(s["load_weight_kg"] for s in assigned)
        load_utilization = total_weight / max(vehicle["capacity_weight_kg"], 1)
        active_minutes = min(480, 120 + len(assigned) * 95 + index * 17) if vehicle["vehicle_id"] in active_ids else 0
        available_minutes = 480 if str(vehicle.get("status", "")).lower() != "maintenance" else 0
        utilization_ratio = active_minutes / available_minutes if available_minutes else 0
        distance_today_km = round(active_minutes * (0.38 if vehicle.get("fuel_type") != "electric" else 0.32), 1)
        usage.append({
            "vehicle_id": vehicle["vehicle_id"],
            "shipment_count": len(assigned),
            "load_utilization": round(load_utilization, 3),
            "utilization_ratio": round(utilization_ratio, 3),
            "active_operating_minutes": active_minutes,
            "available_operating_minutes": available_minutes,
            "distance_today_km": distance_today_km,
            "status": "Active" if vehicle["vehicle_id"] in active_ids else vehicle["status"],
        })
    underused = [u["vehicle_id"] for u in usage if u["shipment_count"] == 0]
    high_use = [u["vehicle_id"] for u in usage if u["utilization_ratio"] >= 0.75 or u["load_utilization"] >= 0.75 or u["shipment_count"] >= 3]
    average_utilization = sum(u["utilization_ratio"] for u in usage) / total_safe
    score = round(min(100, average_utilization * 100), 1)
    return {
        "total_vehicle_count": total,
        "active_vehicle_count": active_count,
        "idle_vehicle_count": idle_count,
        "maintenance_vehicle_count": maintenance_count,
        "unavailable_vehicle_count": unavailable_count,
        "active_vehicle_ratio": round(active_count / total_safe, 3),
        "average_utilization_ratio": round(average_utilization, 3),
        "fleet_utilization_score": score,
        "underused_vehicles": underused,
        "high_use_vehicles": high_use,
        "vehicle_usage": usage,
    }
