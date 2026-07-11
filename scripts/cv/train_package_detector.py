from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    try:
        from ultralytics import YOLO  # type: ignore
    except Exception as exc:
        raise SystemExit("Install ultralytics first: pip install -r requirements-cv.txt") from exc
    if not Path(args.data).exists():
        raise SystemExit(f"Missing data.yaml: {args.data}")
    model = YOLO(args.model)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, project=args.project, name="v1")


if __name__ == "__main__":
    main()
