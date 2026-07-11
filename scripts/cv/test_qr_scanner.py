from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
if ROOT.name == 'cv':
    ROOT = ROOT.parent
ROOT = ROOT.parent if ROOT.name == 'scripts' else ROOT
sys.path.insert(0, str(ROOT))

from database.connection import initialize_database
from database import repositories as repo


def decode_qr(image_path: Path) -> str:
    import cv2  # type: ignore
    image = cv2.imread(str(image_path))
    if image is None:
        raise SystemExit(f"Could not read image: {image_path}")
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(image)
    if not data:
        raise SystemExit(f"QR not decoded from {image_path}")
    return data


def lookup(payload: dict) -> dict | None:
    return repo.row(
        "SELECT p.*, s.sla_deadline, s.status FROM cv_demo_packages p JOIN shipments s ON s.shipment_id=p.shipment_id WHERE p.shipment_id=? AND p.package_id=?",
        (payload["shipment_id"], payload["package_id"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Decode one demo QR label and verify backend/database identity lookup.")
    parser.add_argument("--image", default="data/demo_qr/SHP-LOAD-001.png")
    args = parser.parse_args()
    initialize_database()
    data = decode_qr(Path(args.image))
    payload = json.loads(data)
    row = lookup(payload)
    if not row:
        raise SystemExit(f"Backend lookup: FAILED for {payload}")
    print("QR decoded")
    print(f"Shipment ID: {payload['shipment_id']}")
    print(f"Package ID: {payload['package_id']}")
    print("Backend lookup: SUCCESS")
    print(f"Planned vehicle: {row['planned_vehicle_id']}")
    print(f"Planned route: {row['planned_route_id']}")
    print(f"Current stage: {row['current_stage']}")


if __name__ == "__main__":
    main()
