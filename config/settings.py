from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    app_name: str = "LogiSense AI"
    app_version: str = "1.0.0"
    timezone: str = os.getenv("LOGISENSE_TIMEZONE", "Asia/Jakarta")
    random_seed: int = int(os.getenv("LOGISENSE_RANDOM_SEED", "42"))
    database_path: Path = BASE_DIR / os.getenv("LOGISENSE_DB_PATH", "data/logisense.db")
    model_dir: Path = BASE_DIR / "models"
    simulator_interval_seconds: int = 3
    max_upload_mb: int = 8
    yolo_model_path: Path = BASE_DIR / "models" / "loading_yolo.pt"
    risk_low: float = 0.25
    risk_medium: float = 0.50
    risk_high: float = 0.75
    co2_factor_by_fuel: dict = None
    route_presets: dict = None

    def __post_init__(self):
        object.__setattr__(self, "co2_factor_by_fuel", self.co2_factor_by_fuel or {
            "gasoline": 2.31,
            "diesel": 2.68,
            "electric": 0.42,
        })
        object.__setattr__(self, "route_presets", self.route_presets or {
            "fastest": {"time": 0.60, "fuel": 0.10, "co2": 0.05, "sla": 0.25},
            "greenest": {"time": 0.10, "fuel": 0.25, "co2": 0.55, "sla": 0.10},
            "sla_priority": {"time": 0.20, "fuel": 0.05, "co2": 0.05, "sla": 0.70},
            "balanced_ai": {"time": 0.30, "fuel": 0.20, "co2": 0.20, "sla": 0.30},
        })


settings = Settings()
