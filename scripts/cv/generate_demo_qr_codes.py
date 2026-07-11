from __future__ import annotations

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


OUT = Path("data/demo_qr")


def package_rows() -> list[dict]:
    initialize_database()
    rows = repo.rows(
        "SELECT package_id, shipment_id, qr_payload_json FROM cv_demo_packages WHERE shipment_id IN ('SHP-DMG-001','SHP-LOAD-001','SHP-LOAD-002','SHP-HUB-001') ORDER BY shipment_id"
    )
    if len(rows) < 4:
        raise SystemExit("CV demo packages are missing. Run: python scripts\\seed_cv_demo_data.py")
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        import qrcode  # type: ignore
        from PIL import Image, ImageDraw, ImageFont
    except Exception as exc:
        (OUT / "README.txt").write_text("Install qrcode[pil] from requirements-cv.txt to generate PNG QR labels.\n", encoding="utf-8")
        raise SystemExit(f"qrcode/Pillow is not installed: {exc}") from exc

    manifest = []
    for row in package_rows():
        payload = json.loads(row["qr_payload_json"])
        payload_text = json.dumps(payload, separators=(",", ":"))
        qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=3)
        qr.add_data(payload_text)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        label_w = max(qr_img.width, 620)
        label_h = qr_img.height + 132
        label = Image.new("RGB", (label_w, label_h), "white")
        label.paste(qr_img, ((label_w - qr_img.width) // 2, 12))
        draw = ImageDraw.Draw(label)
        font = ImageFont.load_default()
        lines = [row["shipment_id"], row["package_id"], "Payload: shipment_id + package_id + version"]
        y = qr_img.height + 22
        for line in lines:
            draw.text((24, y), line, fill="black", font=font)
            y += 28
        path = OUT / f"{row['shipment_id']}.png"
        label.save(path)
        manifest.append({"shipment_id": row["shipment_id"], "package_id": row["package_id"], "file": str(path), "payload": payload})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {len(manifest)} printable QR labels in {OUT.resolve()}")
    for item in manifest:
        print(f"- {item['shipment_id']}: {Path(item['file']).resolve()}")


if __name__ == "__main__":
    main()
