from __future__ import annotations

import json
from typing import Any


class QRReader:
    def __init__(self) -> None:
        import cv2  # type: ignore
        self.detector = cv2.QRCodeDetector()

    def scan(self, frame) -> dict | None:
        data, points, _ = self.detector.detectAndDecode(frame)
        if not data:
            return None
        payload: dict[str, Any]
        try:
            parsed = json.loads(data)
            payload = parsed if isinstance(parsed, dict) else {"shipment_id": str(parsed)}
        except Exception:
            payload = {"shipment_id": data}
        if "package_id" not in payload and payload.get("shipment_id"):
            payload["package_id"] = "PKG-" + str(payload["shipment_id"]).split("-")[-1]
        return {"raw": data, "payload": payload, "points": points.tolist() if points is not None else None}
