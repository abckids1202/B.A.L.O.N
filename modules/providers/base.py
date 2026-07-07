from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Protocol


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class ProviderHealth:
    domain: str
    provider_name: str
    health: str
    latest_update: str | None
    source_type: str
    is_simulated: bool
    last_error: str | None = None
    stale_after_minutes: int = 30

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrafficContext:
    shipment_id: str
    route_id: str
    traffic_index: float
    average_speed_kmh: float
    travel_time_multiplier: float
    observed_at: str
    provider: str
    source_type: str = "SYNTHETIC DEMO"
    available: bool = True
    is_simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WeatherContext:
    shipment_id: str
    condition: str
    rainfall_mm: float
    temperature_c: float
    severity_index: float
    observed_at: str
    provider: str
    source_type: str = "SYNTHETIC DEMO"
    available: bool = True
    is_simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GPSContext:
    shipment_id: str
    vehicle_id: str
    lat: float
    lon: float
    speed_kmh: float
    route_deviation_count: int
    observed_at: str
    provider: str
    source_type: str = "SYNTHETIC DEMO"
    available: bool = True
    is_simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HubContext:
    hub_id: str
    shipment_id: str
    arrival_rate_per_hour: float
    departure_rate_per_hour: float
    queue_size: int
    average_dwell_time_min: float
    processing_rate_per_hour: float
    sorting_time_min: float
    loading_time_min: float
    unloading_time_min: float
    workforce_capacity_index: float
    current_delayed_shipments: int
    current_total_shipments: int
    observed_at: str
    provider: str
    source_type: str = "SYNTHETIC DEMO"
    available: bool = True
    is_simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TrafficProvider(Protocol):
    name: str
    def current(self, shipment_id: str) -> TrafficContext: ...
    def health(self) -> ProviderHealth: ...


class WeatherProvider(Protocol):
    name: str
    def current(self, shipment_id: str) -> WeatherContext: ...
    def health(self) -> ProviderHealth: ...


class GPSProvider(Protocol):
    name: str
    def current(self, shipment_id: str) -> GPSContext: ...
    def health(self) -> ProviderHealth: ...


class HubProvider(Protocol):
    name: str
    def current(self, shipment_id: str) -> HubContext: ...
    def health(self) -> ProviderHealth: ...
