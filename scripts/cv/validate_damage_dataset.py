from __future__ import annotations

import json
from pathlib import Path


def parse_names(data_yaml: Path) -> list[str]:
    for line in data_yaml.read_text(encoding="utf-8-sig").splitlines():
        if line.strip().startswith("names:"):
            raw = line.split(":", 1)[1].strip()
            try:
                return list(json.loads(raw.replace("'", '"')))
            except Exception:
                return [item.strip(" '\"") for item in raw.strip("[]").split(",") if item.strip()]
    return []


def validate_dataset(path: Path) -> dict:
    data_yaml = path / "data.yaml"
    result = {
        "path": str(path),
        "exists": path.exists(),
        "data_yaml": str(data_yaml) if data_yaml.exists() else None,
        "classes": parse_names(data_yaml) if data_yaml.exists() else [],
        "splits": {},
        "weights": [str(p) for p in path.rglob("*.pt")] + [str(p) for p in path.rglob("*.onnx")] if path.exists() else [],
    }
    for split in ["train", "valid", "test"]:
        images = path / split / "images"
        labels = path / split / "labels"
        result["splits"][split] = {
            "images": len(list(images.glob("*"))) if images.exists() else 0,
            "labels": len(list(labels.glob("*.txt"))) if labels.exists() else 0,
        }
    return result


if __name__ == "__main__":
    print(json.dumps(validate_dataset(Path("Parcel Damage Detection.v2-roboflow-instant-2--eval-.yolov11")), indent=2))
