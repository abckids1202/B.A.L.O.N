from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True)
    parser.add_argument("--data", required=True)
    args = parser.parse_args()
    try:
        from ultralytics import YOLO  # type: ignore
    except Exception as exc:
        raise SystemExit("Install ultralytics first: pip install -r requirements-cv.txt") from exc
    if not Path(args.weights).exists():
        raise SystemExit(f"Missing weights: {args.weights}")
    metrics = YOLO(args.weights).val(data=args.data)
    print(metrics)


if __name__ == "__main__":
    main()
