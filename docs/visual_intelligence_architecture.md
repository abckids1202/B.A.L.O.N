# Visual Intelligence Architecture

Routix uses four computer-vision feature workflows as operational signals, not isolated ML demos.

## End-to-end chain

1. Package arrives.
2. Package Damage Detection runs on the parcel damage dataset.
3. QR Scan and Wrong Loading Detection reuses the package and label detector, decodes the shipment QR, then validates the assignment from the backend.
4. Loading Compliance tracks packages crossing dock and vehicle regions of interest.
5. Vehicle departs.
6. Hub Congestion Detection uses package detection plus ByteTrack-style tracking and fixed hub zones.
7. ETA, SLA risk, routing, dashboards, package twins, hub twins, and analytics refresh.

## Model A: Package Vision

Model A covers package quality, label/QR visibility, wrong loading, and loading compliance. Wrong loading intentionally does not train another detector. The detector finds packages and labels; OpenCV QRCodeDetector or pyzbar reads a stable shipment ID such as `SHP-1028`; the backend returns planned vehicle, hub, route, priority, SLA, and destination context.

## Model B: Hub Vision

Model B reuses package detection at the hub and adds tracking. In production, `supervision.ByteTrack` can assign track IDs to package detections. Fixed polygons represent inbound, queue, sorting, loading, and outbound zones. Per-frame zone membership produces dwell time, queue length, occupancy ratio, congestion severity, and overflow probability.

## Current implementation status

The app now exposes deterministic demo endpoints under `/api/visual-intelligence/*`. They write normalized operational signals and interventions into the same backend tables as routing, SLA, hub, and package digital twin workflows. The local YOLO folders are treated as dataset assets; no model weights are claimed unless `.pt` or `.onnx` exports are present.
