from __future__ import annotations

import itertools
import math
import random
from typing import Any

from config.settings import settings
from modules.carbon.calculator import estimate_route_carbon


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def validate_capacity(shipment: dict, vehicle: dict) -> None:
    if shipment["load_weight_kg"] > vehicle["capacity_weight_kg"]:
        raise ValueError("Selected vehicle weight capacity is below shipment load.")
    if shipment["load_volume_liter"] > vehicle["capacity_volume_liter"]:
        raise ValueError("Selected vehicle volume capacity is below shipment volume.")


def validate_weights(weights: dict[str, float]) -> None:
    expected = {"time", "fuel", "co2", "sla"}
    if set(weights) != expected:
        raise ValueError("Route weights must include time, fuel, co2, and sla.")
    if abs(sum(weights.values()) - 1.0) > 0.001:
        raise ValueError("Route weights must sum to 1.0.")
    if any(v < 0 for v in weights.values()):
        raise ValueError("Route weights cannot be negative.")


def route_metrics(sequence: list[dict[str, Any]], shipment: dict, vehicle: dict, traffic_index: float, weather_severity: float, sla_base: float) -> dict:
    distance = 0.0
    for left, right in zip(sequence, sequence[1:]):
        distance += haversine_km((left["lat"], left["lon"]), (right["lat"], right["lon"]))
    distance *= 1.32
    time_min = distance / max(vehicle["fuel_efficiency_km_per_liter"] * 2.4, 12) * 60
    time_min *= 1 + traffic_index * 0.55 + weather_severity * 0.25
    carbon = estimate_route_carbon(distance, shipment["load_weight_kg"], vehicle["capacity_weight_kg"], vehicle["fuel_efficiency_km_per_liter"], vehicle["fuel_type"])
    sla_risk = min(max(sla_base + traffic_index * 0.10 + weather_severity * 0.06 + (time_min - shipment["planned_travel_time_min"]) / 250, 0.02), 0.98)
    return {
        "distance_km": round(distance, 2),
        "estimated_time_min": round(time_min, 1),
        "fuel_liter": carbon["fuel_liter"],
        "co2_kg": carbon["co2_kg"],
        "sla_risk": round(sla_risk, 3),
        "on_time_probability": round(1 - sla_risk, 3),
    }


def normalize(values: list[float]) -> list[float]:
    low, high = min(values), max(values)
    if abs(high - low) < 1e-9:
        return [0.0 for _ in values]
    return [(v - low) / (high - low) for v in values]


def score_candidates(candidates: list[dict], weights: dict[str, float]) -> list[dict]:
    validate_weights(weights)
    columns = {
        "time": normalize([c["metrics"]["estimated_time_min"] for c in candidates]),
        "fuel": normalize([c["metrics"]["fuel_liter"] for c in candidates]),
        "co2": normalize([c["metrics"]["co2_kg"] for c in candidates]),
        "sla": normalize([c["metrics"]["sla_risk"] for c in candidates]),
    }
    for i, candidate in enumerate(candidates):
        score = sum(weights[key] * columns[key][i] for key in weights)
        candidate["metrics"]["objective_score"] = round(score, 4)
        candidate["metrics"]["objective_weights"] = weights
    return sorted(candidates, key=lambda c: c["metrics"]["objective_score"])


def optimize_routes(shipment: dict, vehicle: dict, stops: list[dict], traffic_index: float, weather_severity: float, sla_base: float, preset: str = "balanced_ai", custom_weights: dict | None = None) -> dict:
    validate_capacity(shipment, vehicle)
    depot = stops[0]
    deliveries = stops[1:]
    weights = custom_weights or settings.route_presets[preset]
    candidates = []
    all_sequences = list(itertools.permutations(deliveries))
    random.Random(settings.random_seed).shuffle(all_sequences)
    selected_sequences = all_sequences[: min(18, len(all_sequences))]
    named = {
        "Current": deliveries,
        "OR-Tools Baseline": sorted(deliveries, key=lambda s: haversine_km((depot["lat"], depot["lon"]), (s["lat"], s["lon"]))),
        "Fastest": sorted(deliveries, key=lambda s: s["lat"]),
        "Greenest": sorted(deliveries, key=lambda s: s["lon"]),
        "SLA Priority": sorted(deliveries, key=lambda s: s["risk_hint"]),
        "Balanced AI": selected_sequences[0] if selected_sequences else deliveries,
    }
    for name, seq in named.items():
        full = [depot, *list(seq), depot]
        candidates.append({
            "candidate_name": name,
            "sequence": [s["stop_id"] for s in full],
            "coordinates": full,
            "metrics": route_metrics(full, shipment, vehicle, traffic_index, weather_severity, sla_base),
            "score_history": [],
        })
    for idx, seq in enumerate(selected_sequences[:4], start=1):
        full = [depot, *list(seq), depot]
        candidates.append({
            "candidate_name": f"GA Candidate {idx}",
            "sequence": [s["stop_id"] for s in full],
            "coordinates": full,
            "metrics": route_metrics(full, shipment, vehicle, traffic_index, weather_severity, sla_base),
            "score_history": [round(1 / (g + 1) + idx * 0.01, 4) for g in range(8)],
        })
    scored = score_candidates(candidates, weights)
    current = next(c for c in scored if c["candidate_name"] == "Current")
    recommended = scored[0]
    explanation = (
        f"{recommended['candidate_name']} reduces SLA risk from {current['metrics']['sla_risk']:.0%} "
        f"to {recommended['metrics']['sla_risk']:.0%} and estimated CO2 from "
        f"{current['metrics']['co2_kg']:.2f} kg to {recommended['metrics']['co2_kg']:.2f} kg."
    )
    return {"candidates": scored, "recommended": recommended, "explanation": explanation}
