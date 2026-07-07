from __future__ import annotations

from typing import Any

SLA_FEATURES = [
    "traffic_index",
    "weather_severity",
    "hub_dwell_excess",
    "sla_buffer_minutes",
    "route_distance_km",
    "load_weight_kg",
    "loading_compliance_score",
]


def sla_model_vector(features: dict[str, Any]) -> list[float]:
    return [float(features[name]) for name in SLA_FEATURES]
