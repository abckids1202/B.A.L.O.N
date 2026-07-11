from __future__ import annotations

import json
from pathlib import Path


SHIPMENTS = ["SHP-1028", "SHP-DMG-001", "SHP-LOAD-001"]
OUT = Path("data/demo_qr")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    try:
        import qrcode  # type: ignore
    except Exception:
        (OUT / "README.txt").write_text("Install qrcode[pil] from requirements-cv.txt to generate PNG QR labels.\n", encoding="utf-8")
        print("qrcode is not installed; wrote data/demo_qr/README.txt")
        return
    for shipment_id in SHIPMENTS:
        img = qrcode.make(shipment_id)
        path = OUT / f"{shipment_id}.png"
        img.save(path)
        manifest.append({"shipment_id": shipment_id, "file": str(path), "payload": shipment_id})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {len(manifest)} QR labels in {OUT}")


if __name__ == "__main__":
    main()
