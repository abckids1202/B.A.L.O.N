from __future__ import annotations

from config.settings import settings


def estimate_route_carbon(distance_km: float, load_weight_kg: float, capacity_weight_kg: float, fuel_efficiency_km_per_liter: float, fuel_type: str) -> dict:
    if fuel_efficiency_km_per_liter <= 0:
        raise ValueError("Fuel efficiency must be positive.")
    if capacity_weight_kg <= 0:
        raise ValueError("Vehicle capacity must be positive.")
    estimated_fuel_liter = distance_km / fuel_efficiency_km_per_liter
    factor = settings.co2_factor_by_fuel.get(fuel_type, settings.co2_factor_by_fuel["gasoline"])
    load_ratio = min(max(load_weight_kg / capacity_weight_kg, 0), 1.5)
    load_adjustment = 1.0 + 0.18 * load_ratio
    co2 = estimated_fuel_liter * factor * load_adjustment
    return {
        "fuel_liter": round(estimated_fuel_liter, 3),
        "co2_kg": round(co2, 3),
        "source": "Deterministic Carbon Baseline",
        "assumptions": {
            "fuel_factor_kg_per_liter": factor,
            "load_adjustment": round(load_adjustment, 3),
            "not_certified_emissions": True,
        },
    }
