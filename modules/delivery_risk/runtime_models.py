from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib

from config.settings import settings
from modules.delivery_risk.delay_features import DELAY_FEATURES, delay_model_vector
from modules.delivery_risk.features import fallback_delay, fallback_sla_probability
from modules.delivery_risk.sla_features import SLA_FEATURES, sla_model_vector


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return joblib.load(path)
    except Exception:
        return None


def predict_delay(features: dict[str, Any]) -> dict[str, Any]:
    artifact = _load(settings.model_dir / "delay_model.joblib")
    if artifact and artifact.get("features") == DELAY_FEATURES:
        value = float(artifact["model"].predict([delay_model_vector(features)])[0])
        return {
            "value": round(max(value, 0.0), 1),
            "source": "Trained Delay Model",
            "version": "v1",
            "fallback": False,
        }
    return {
        "value": fallback_delay(features),
        "source": "Rule Fallback",
        "version": "fallback-v1",
        "fallback": True,
    }


def predict_sla(features: dict[str, Any], predicted_delay: float) -> dict[str, Any]:
    artifact = _load(settings.model_dir / "sla_model.joblib")
    if artifact and artifact.get("features") == SLA_FEATURES and hasattr(artifact["model"], "predict_proba"):
        probability = float(artifact["model"].predict_proba([sla_model_vector(features)])[0][1])
        return {
            "value": round(min(max(probability, 0.0), 1.0), 3),
            "source": "Trained SLA Model",
            "version": "v1",
            "fallback": False,
        }
    return {
        "value": fallback_sla_probability(features, predicted_delay),
        "source": "Rule Fallback",
        "version": "fallback-v1",
        "fallback": True,
    }
