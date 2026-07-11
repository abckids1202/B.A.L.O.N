# CV Demo QR Packages

Run:

```powershell
python scripts\seed_cv_demo_data.py
python scripts\cv\generate_demo_qr_codes.py
python scripts\cv\test_qr_scanner.py --image data\demo_qr\SHP-LOAD-001.png
```

QR payloads intentionally contain only stable identity:

```json
{"shipment_id":"SHP-LOAD-001","package_id":"PKG-LOAD-001","version":1}
```

Mutable state such as active vehicle, current hub, ETA, SLA risk, and route status stays in the backend.

Hero labels:

- `SHP-DMG-001` / `PKG-DMG-001`: package quality damage demo
- `SHP-LOAD-001` / `PKG-LOAD-001`: wrong/correct loading demo expecting `VAN-021`
- `SHP-LOAD-002` / `PKG-LOAD-002`: loading compliance demo expecting `VAN-044`
- `SHP-HUB-001` / `PKG-HUB-001`: hub congestion demo

Print labels at roughly 4-6 cm wide, attach them flatly, avoid glossy reflections, and test at 30 cm, 60 cm, slight angle, and normal room light.
