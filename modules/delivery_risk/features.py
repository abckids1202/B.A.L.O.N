from __future__ import annotations

from datetime import datetime
from typing import Any


def risk_level(probability: float) -> str:
    if probability >= 0.75:
        return "Critical"
    if probability >= 0.50:
        return "High"
    if probability >= 0.25:
        return "Medium"
    return "Low"


def build_features(snapshot: dict[str, Any]) -> dict[str, float]:
    shipment = snapshot["shipment"]
    traffic = snapshot["traffic"]
    weather = snapshot["weather"]
    hub = snapshot["hub_event"]
    gps = snapshot["gps"]
    planned = max(float(shipment["planned_travel_time_min"]), 1.0)
    historical = float(shipment["historical_travel_time_min"])
    dwell_excess = max(float(hub["average_dwell_time_min"]) - float(snapshot["hub"]["normal_dwell_time_min"]), 0)
    deadline = datetime.fromisoformat(shipment["sla_deadline"])
    now = datetime.fromisoformat(traffic["captured_at"])
    eta_buffer = max((deadline - now).total_seconds() / 60.0 - planned, -180)
    return {
        "historical_travel_time_min": historical,
        "planned_travel_time_min": planned,
        "traffic_index": float(traffic["traffic_index"]),
        "traffic_delay_ratio": historical / planned,
        "weather_severity": float(weather["severity_index"]),
        "rainfall_mm": float(weather["rainfall_mm"]),
        "hub_dwell_excess": dwell_excess,
        "sla_buffer_minutes": eta_buffer,
        "speed_deviation": float(gps["speed_kmh"]) / max(float(traffic["average_speed_kmh"]), 1),
        "route_distance_km": float(shipment["route_distance_km"]),
        "load_weight_kg": float(shipment["load_weight_kg"]),
        "priority_score": {"Standard": 0.3, "Express": 0.7, "Critical": 1.0}.get(shipment["priority"], 0.4),
        "loading_compliance_score": float(shipment.get("loading_compliance_score") or 80),
    }


def fallback_delay(features: dict[str, float]) -> float:
    delay = (
        features["traffic_index"] * 38
        + features["weather_severity"] * 24
        + features["hub_dwell_excess"] * 0.65
        + max(-features["sla_buffer_minutes"], 0) * 0.25
        + max(0, 85 - features["loading_compliance_score"]) * 0.35
        - 12
    )
    return round(max(delay, 0), 1)


def fallback_sla_probability(features: dict[str, float], predicted_delay: float) -> float:
    pressure = (
        predicted_delay / 90
        + features["traffic_index"] * 0.30
        + features["weather_severity"] * 0.18
        + min(features["hub_dwell_excess"] / 90, 1) * 0.24
        + features["priority_score"] * 0.10
        - max(features["sla_buffer_minutes"], 0) / 240
    )
    return round(min(max(pressure, 0.03), 0.98), 3)


def factor_text(features: dict[str, float], predicted_delay: float) -> list[str]:
    factors = [
        f"Traffic index is {features['traffic_index']:.2f}.",
        f"Hub dwell exceeds normal by {features['hub_dwell_excess']:.0f} minutes.",
        f"Rainfall is {features['rainfall_mm']:.1f} mm with weather severity {features['weather_severity']:.2f}.",
        f"SLA buffer is {features['sla_buffer_minutes']:.0f} minutes versus predicted delay {predicted_delay:.0f} minutes.",
    ]
    return factors
