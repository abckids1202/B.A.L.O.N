from __future__ import annotations

from pydantic import BaseModel, Field


class RouteOptimizeRequest(BaseModel):
    shipment_id: str
    vehicle_id: str | None = None
    preset: str = "balanced_ai"
    weights: dict[str, float] | None = None


class CarbonEstimateRequest(BaseModel):
    shipment_id: str
    vehicle_id: str
    distance_km: float = Field(gt=0)
    route_name: str = "Ad hoc"
