from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OperationalEvent:
    event_id: str
    event_type: str
    entity_type: str
    entity_id: str
    observed_at: str
    received_at: str
    source: str
    is_simulated: bool
    payload: dict[str, Any]
    schema_version: str = "event.v1"
