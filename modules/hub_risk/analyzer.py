from __future__ import annotations


def derive_hub_features(event: dict, hub: dict) -> dict:
    queue_growth = event["arrival_rate_per_hour"] - event["departure_rate_per_hour"]
    dwell_excess = event["average_dwell_time_min"] - hub["normal_dwell_time_min"]
    processing_utilization = event["arrival_rate_per_hour"] / max(event["processing_rate_per_hour"], 1)
    delay_pressure = event["current_delayed_shipments"] / max(event["current_total_shipments"], 1)
    return {
        "queue_growth": round(queue_growth, 2),
        "dwell_excess": round(dwell_excess, 2),
        "processing_utilization": round(processing_utilization, 3),
        "delay_pressure": round(delay_pressure, 3),
    }


def risk_level(score: float) -> str:
    if score >= 85:
        return "Critical"
    if score >= 65:
        return "High"
    if score >= 40:
        return "Watch"
    return "Normal"


def analyze_hub(event: dict, hub: dict) -> dict:
    f = derive_hub_features(event, hub)
    score = (
        max(f["queue_growth"], 0) * 2.4
        + max(f["dwell_excess"], 0) * 1.1
        + f["processing_utilization"] * 28
        + f["delay_pressure"] * 35
        + max(event["queue_size"] - 12, 0) * 1.2
    )
    score = round(max(0, min(score, 100)), 1)
    stages = {
        "Inbound receiving": event["unloading_time_min"] / 18,
        "Sorting": event["sorting_time_min"] / 22,
        "Loading": event["loading_time_min"] / 20,
        "Outbound dispatch": max(f["queue_growth"], 0) / 10,
    }
    bottleneck = max(stages, key=stages.get)
    return {
        "hub_id": hub["hub_id"],
        "congestion_score": score,
        "risk_level": risk_level(score),
        "queue_growth": f["queue_growth"],
        "dwell_excess": f["dwell_excess"],
        "processing_utilization": f["processing_utilization"],
        "delay_pressure": f["delay_pressure"],
        "likely_bottleneck": bottleneck,
        "bottleneck_evidence": {k: round(v, 2) for k, v in stages.items()},
        "estimated_delayed_shipments": int(event["current_delayed_shipments"] + max(f["queue_growth"], 0) * 1.5),
    }
