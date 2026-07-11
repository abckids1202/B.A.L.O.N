from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _parse_names(data_yaml: Path) -> list[str]:
    if not data_yaml.exists():
        return []
    for line in data_yaml.read_text(encoding="utf-8-sig").splitlines():
        if line.strip().startswith("names:"):
            raw = line.split(":", 1)[1].strip()
            try:
                return list(json.loads(raw.replace("'", '"')))
            except Exception:
                return [item.strip(" '\"") for item in raw.strip("[]").split(",") if item.strip()]
    return []


def inspect_asset(folder_name: str) -> dict:
    root = ROOT / folder_name
    weights = sorted([*root.rglob("*.pt"), *root.rglob("*.onnx")]) if root.exists() else []
    data_yaml = root / "data.yaml"
    asset_type = "TRAINED_MODEL" if weights else "YOLO_DATASET" if data_yaml.exists() else "UNKNOWN"
    return {
        "folder": folder_name,
        "path": str(root),
        "exists": root.exists(),
        "asset_type": asset_type,
        "data_yaml": str(data_yaml) if data_yaml.exists() else None,
        "classes": _parse_names(data_yaml),
        "weights": [str(path) for path in weights],
        "status": "LOADED" if weights else "WEIGHTS_MISSING",
    }


def registry() -> dict:
    return {
        "package": inspect_asset("Package and label detection.v4i.yolov11"),
        "damage": inspect_asset("Parcel Damage Detection.v2-roboflow-instant-2--eval-.yolov11"),
    }
