# Dispatch Validation Demo

Use `DISPATCH_VALIDATION` mode. Replay fallback: `python scripts/demo_cv_replay.py --scenario WRONG_LOADING`.

The QR payload is only the shipment ID. The backend resolves planned vehicle, hub, route, and SLA state. Wrong vehicle observations create a dispatch block and correction action.
