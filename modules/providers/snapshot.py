from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from database import repositories as repo
from modules.providers.demo import DemoGPSProvider, DemoHubProvider, DemoTrafficProvider, DemoWeatherProvider


@dataclass
class OperationalSnapshot:
    shipment_id: str
    shipment: dict[str, Any]
    vehicle: dict[str, Any] | None
    hub: dict[str, Any]
    traffic: dict[str, Any]
    weather: dict[str, Any]
    gps: dict[str, Any]
    hub_event: dict[str, Any]
    provider_provenance: dict[str, Any]
    environment_mode: str = "SYNTHETIC DEMO"
    schema_version: str = "snapshot.v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OperationalSnapshotBuilder:
    def __init__(self) -> None:
        self.traffic = DemoTrafficProvider()
        self.weather = DemoWeatherProvider()
        self.gps = DemoGPSProvider()
        self.hub_event = DemoHubProvider()

    def build(self, shipment_id: str) -> OperationalSnapshot:
        shipment = repo.row("SELECT * FROM shipments WHERE shipment_id=?", (shipment_id,))
        if not shipment:
            raise ValueError(f"Shipment {shipment_id} not found.")
        vehicle = repo.row("SELECT * FROM vehicles WHERE vehicle_id=?", (shipment.get("vehicle_id"),))
        hub = repo.row("SELECT * FROM hubs WHERE hub_id=?", (shipment["origin_hub"],))
        traffic = self.traffic.current(shipment_id)
        weather = self.weather.current(shipment_id)
        gps = self.gps.current(shipment_id)
        hub_event = self.hub_event.current(shipment_id)
        return OperationalSnapshot(
            shipment_id=shipment_id,
            shipment=shipment,
            vehicle=vehicle,
            hub=hub,
            traffic=traffic.to_dict(),
            weather=weather.to_dict(),
            gps=gps.to_dict(),
            hub_event=hub_event.to_dict(),
            provider_provenance={
                "traffic": traffic.provider,
                "weather": weather.provider,
                "gps": gps.provider,
                "hub": hub_event.provider,
                "shipment": "DemoShipmentProvider",
                "vehicle": "DemoVehicleProvider",
            },
        )
