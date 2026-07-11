# QR Package Identity

Wrong package loading is a reconciliation problem:

```text
Camera -> package/label YOLO -> crop QR/label -> QR decoder -> backend lookup -> compare planned assignment
```

The QR payload should stay small and stable. Use only the shipment ID, for example:

```text
SHP-1028
```

Everything else comes from the backend: planned vehicle, origin hub, destination hub, route, SLA window, priority, and current package twin state. This keeps QR labels durable even when assignments are updated.

Recommended readers:

- `cv2.QRCodeDetector().detectAndDecode(frame)`
- `pyzbar.decode(crop)`

The production correction action is to block dispatch when the observed vehicle does not match the planned vehicle, then require reload and rescan.
