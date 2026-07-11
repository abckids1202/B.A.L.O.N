from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cv_worker.config import ROOT, config


_PACKAGE_MODEL: Any | None = None
_DAMAGE_MODEL: Any | None = None
_CACHE: dict[str, dict] | None = None


@dataclass
class ModelStatus:
    provider: str
    configured_path: str
    resolved_path: str | None
    file_exists: bool
    file_size_bytes: int | None
    status: str
    classes: dict | list | None = None
    normalized_classes: dict | None = None
    device: str = "cpu"
    load_duration_ms: float | None = None
    error: str | None = None


def _resolve(path_text: str | None) -> Path | None:
    if not path_text or not str(path_text).strip():
        return None
    path = Path(str(path_text).strip().strip('"'))
    return path if path.is_absolute() else ROOT / path


def _status(provider: str, configured_path: str, loader, disabled_names: set[str] | None = None) -> tuple[ModelStatus, Any | None]:
    disabled_names = disabled_names or {"disabled", "none", "off"}
    if provider.lower() in disabled_names:
        return ModelStatus(provider, configured_path, None, False, None, "DISABLED"), None
    resolved = _resolve(configured_path)
    if resolved is None:
        return ModelStatus(provider, configured_path, None, False, None, "PATH_NOT_CONFIGURED"), None
    if not resolved.exists():
        return ModelStatus(provider, configured_path, str(resolved), False, None, "FILE_NOT_FOUND"), None
    started = time.perf_counter()
    try:
        model, meta = loader(resolved)
        elapsed = (time.perf_counter() - started) * 1000
        return ModelStatus(
            provider=provider,
            configured_path=configured_path,
            resolved_path=str(resolved),
            file_exists=True,
            file_size_bytes=resolved.stat().st_size,
            status="LOADED",
            classes=meta.get("classes") or meta.get("labels"),
            normalized_classes=meta.get("normalized_classes"),
            device=meta.get("device", config.device),
            load_duration_ms=round(elapsed, 2),
        ), model
    except Exception as exc:
        elapsed = (time.perf_counter() - started) * 1000
        return ModelStatus(
            provider=provider,
            configured_path=configured_path,
            resolved_path=str(resolved),
            file_exists=True,
            file_size_bytes=resolved.stat().st_size,
            status="LOAD_FAILED",
            device=config.device,
            load_duration_ms=round(elapsed, 2),
            error=str(exc),
        ), None


def _load_package(path: Path):
    from ultralytics import YOLO  # type: ignore
    model = YOLO(str(path))
    names = dict(getattr(model, "names", {}) or {})
    normalized = {str(name): "PACKAGE" for name in names.values()}
    return model, {"classes": {str(k): v for k, v in names.items()}, "normalized_classes": normalized, "device": config.device}


def _load_damage(path: Path):
    from cv_worker.detectors.damage_classifier import PyTorchDamageClassifier
    model = PyTorchDamageClassifier(path)
    return model, {"labels": model.labels, "device": model.device_name}


def refresh_registry() -> dict:
    global _PACKAGE_MODEL, _DAMAGE_MODEL, _CACHE
    package_status, _PACKAGE_MODEL = _status(config.package_provider, config.package_model_path, _load_package)
    damage_status, _DAMAGE_MODEL = _status(config.damage_provider, config.damage_model_path, _load_damage)
    _CACHE = {"package": asdict(package_status), "damage": asdict(damage_status)}
    return _CACHE


def registry() -> dict:
    global _CACHE
    if _CACHE is None:
        return refresh_registry()
    return _CACHE


def package_model():
    if _CACHE is None:
        refresh_registry()
    return _PACKAGE_MODEL


def damage_model():
    if _CACHE is None:
        refresh_registry()
    return _DAMAGE_MODEL


def print_startup_diagnostics() -> None:
    assets = registry()
    for title, item in [("PACKAGE MODEL", assets["package"]), ("DAMAGE MODEL", assets["damage"])]:
        print(f"\n{title}")
        print(f"Provider: {item.get('provider')}")
        print(f"Configured path: {item.get('configured_path')}")
        print(f"Resolved path: {item.get('resolved_path')}")
        print(f"Exists: {item.get('file_exists')}")
        print(f"Status: {item.get('status')}")
        if item.get("classes"):
            print(f"Classes/labels: {item.get('classes')}")
        if item.get("error"):
            print(f"Error: {item.get('error')}")
