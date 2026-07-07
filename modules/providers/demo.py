from __future__ import annotations

from database import repositories as repo
from modules.providers.base import (
    GPSContext,
    HubContext,
    ProviderHealth,
    TrafficContext,
    WeatherContext,
)


def _latest_update(table: str, column: str = "captured_at") -> str | None:
    row = repo.row(f"SELECT {column} AS observed_at FROM {table} ORDER BY {column} DESC LIMIT 1")
    return row["observed_at"] if row else None


class DemoTrafficProvider:
    name = "DemoTrafficProvider"

    def current(self, shipment_id: str) -> TrafficContext:
        row = repo.row("SELECT * FROM traffic_snapshots WHERE shipment_id=? ORDER BY captured_at DESC, id DESC LIMIT 1", (shipment_id,))
        if not row:
            raise ValueError(f"No traffic context for {shipment_id}.")
        return TrafficContext(
            shipment_id=shipment_id,
            route_id=row.get("route_id") or "unknown",
            traffic_index=float(row["traffic_index"]),
            average_speed_kmh=float(row["average_speed_kmh"]),
            travel_time_multiplier=float(row["travel_time_multiplier"]),
            observed_at=row["captured_at"],
            provider=self.name,
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth("Traffic", self.name, "DEMO", _latest_update("traffic_snapshots"), "SYNTHETIC DEMO", True)


class DemoWeatherProvider:
    name = "DemoWeatherProvider"

    def current(self, shipment_id: str) -> WeatherContext:
        row = repo.row("SELECT * FROM weather_snapshots WHERE shipment_id=? ORDER BY captured_at DESC, id DESC LIMIT 1", (shipment_id,))
        if not row:
            raise ValueError(f"No weather context for {shipment_id}.")
        return WeatherContext(
            shipment_id=shipment_id,
            condition=row["condition"],
            rainfall_mm=float(row["rainfall_mm"]),
            temperature_c=float(row["temperature_c"]),
            severity_index=float(row["severity_index"]),
            observed_at=row["captured_at"],
            provider=self.name,
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth("Weather", self.name, "DEMO", _latest_update("weather_snapshots"), "SYNTHETIC DEMO", True)


class DemoGPSProvider:
    name = "DemoGPSProvider"

    def current(self, shipment_id: str) -> GPSContext:
        row = repo.row("SELECT * FROM gps_events WHERE shipment_id=? ORDER BY captured_at DESC, id DESC LIMIT 1", (shipment_id,))
        if not row:
            raise ValueError(f"No GPS context for {shipment_id}.")
        return GPSContext(
            shipment_id=shipment_id,
            vehicle_id=row["vehicle_id"],
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            speed_kmh=float(row["speed_kmh"]),
            route_deviation_count=int(row["route_deviation_count"]),
            observed_at=row["captured_at"],
            provider=self.name,
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth("GPS", self.name, "DEMO", _latest_update("gps_events"), "SYNTHETIC DEMO", True)


class DemoHubProvider:
    name = "DemoHubProvider"

    def current(self, shipment_id: str) -> HubContext:
        row = repo.row("SELECT * FROM hub_events WHERE shipment_id=? ORDER BY captured_at DESC, id DESC LIMIT 1", (shipment_id,))
        if not row:
            raise ValueError(f"No hub context for {shipment_id}.")
        return HubContext(
            hub_id=row["hub_id"],
            shipment_id=shipment_id,
            arrival_rate_per_hour=float(row["arrival_rate_per_hour"]),
            departure_rate_per_hour=float(row["departure_rate_per_hour"]),
            queue_size=int(row["queue_size"]),
            average_dwell_time_min=float(row["average_dwell_time_min"]),
            processing_rate_per_hour=float(row["processing_rate_per_hour"]),
            sorting_time_min=float(row["sorting_time_min"]),
            loading_time_min=float(row["loading_time_min"]),
            unloading_time_min=float(row["unloading_time_min"]),
            workforce_capacity_index=float(row["workforce_capacity_index"]),
            current_delayed_shipments=int(row["current_delayed_shipments"]),
            current_total_shipments=int(row["current_total_shipments"]),
            observed_at=row["captured_at"],
            provider=self.name,
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth("Hub", self.name, "DEMO", _latest_update("hub_events"), "SYNTHETIC DEMO", True)


def provider_status() -> list[dict]:
    return [
        DemoTrafficProvider().health().to_dict(),
        DemoWeatherProvider().health().to_dict(),
        DemoGPSProvider().health().to_dict(),
        DemoHubProvider().health().to_dict(),
        ProviderHealth("Shipment/ERP", "DemoShipmentProvider", "DEMO", None, "SYNTHETIC DEMO", True).to_dict(),
        ProviderHealth("Vehicle/Fleet", "DemoVehicleProvider", "DEMO", None, "SYNTHETIC DEMO", True).to_dict(),
    ]
