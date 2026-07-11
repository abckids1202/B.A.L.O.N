from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "demo_markers"


MARKERS = [
    {"marker_id": 1, "shipment_id": "SHP-DMG-001", "package_id": "PKG-DMG-001", "intended_module": "PACKAGE_QUALITY"},
    {"marker_id": 2, "shipment_id": "SHP-LOAD-001", "package_id": "PKG-LOAD-001", "intended_module": "DISPATCH_VALIDATION"},
    {"marker_id": 3, "shipment_id": "SHP-LOAD-002", "package_id": "PKG-LOAD-002", "intended_module": "LOADING_COMPLIANCE"},
    {"marker_id": 4, "shipment_id": "SHP-HUB-001", "package_id": "PKG-HUB-001", "intended_module": "HUB_VISION"},
    {"marker_id": 5, "shipment_id": "SHP-LOAD-001", "package_id": "PKG-PROP-005", "intended_module": "LOADING_COMPLIANCE"},
    {"marker_id": 6, "shipment_id": "SHP-LOAD-001", "package_id": "PKG-PROP-006", "intended_module": "LOADING_COMPLIANCE"},
    {"marker_id": 7, "shipment_id": "SHP-HUB-001", "package_id": "PKG-PROP-007", "intended_module": "HUB_VISION"},
    {"marker_id": 8, "shipment_id": "SHP-HUB-001", "package_id": "PKG-PROP-008", "intended_module": "HUB_VISION"},
    {"marker_id": 9, "shipment_id": "SHP-HUB-001", "package_id": "PKG-PROP-009", "intended_module": "HUB_VISION"},
    {"marker_id": 10, "shipment_id": "SHP-HUB-001", "package_id": "PKG-PROP-010", "intended_module": "HUB_VISION"},
]


def main() -> None:
    import cv2  # type: ignore
    if not hasattr(cv2, "aruco"):
        raise SystemExit("OpenCV ArUco module is unavailable. Install opencv-contrib-python.")
    OUT.mkdir(parents=True, exist_ok=True)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    manifest = {"markers": []}
    for item in MARKERS:
        marker = cv2.aruco.generateImageMarker(dictionary, item["marker_id"], 560)
        canvas = 255 * __import__("numpy").ones((720, 720), dtype="uint8")
        canvas[80:640, 80:640] = marker
        filename = f"MARKER-{item['marker_id']:02d}-{item['shipment_id']}.png"
        cv2.imwrite(str(OUT / filename), canvas)
        manifest["markers"].append({**item, "file": filename})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {len(MARKERS)} ArUco markers in {OUT}")
    for item in manifest["markers"]:
        print(f"- {item['file']} -> {item['shipment_id']} / {item['package_id']}")


if __name__ == "__main__":
    main()
