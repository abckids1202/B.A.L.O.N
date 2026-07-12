from __future__ import annotations

import time

from cv_worker.runtime import runtime


MODE_KEYS = {
    ord("1"): "PACKAGE_QUALITY",
    ord("2"): "DISPATCH_VALIDATION",
    ord("3"): "LOADING_COMPLIANCE",
    ord("4"): "HUB_VISION",
}

MODE_LABELS = {
    "PACKAGE_QUALITY": "Package Quality",
    "DISPATCH_VALIDATION": "Dispatch Validation",
    "LOADING_COMPLIANCE": "Loading Compliance",
    "HUB_VISION": "Hub Congestion",
}


def _text(cv2, img, text, x, y, scale=.56, color=(15, 23, 42), weight=1):
    cv2.putText(img, str(text), (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, weight, cv2.LINE_AA)


def _panel(cv2, img, x1, y1, x2, y2, title):
    cv2.rectangle(img, (x1, y1), (x2, y2), (248, 250, 252), -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), (203, 213, 225), 1)
    _text(cv2, img, title, x1 + 14, y1 + 28, .58, (30, 64, 175), 2)


def _backend_decision(status: dict) -> tuple[str, str, str]:
    last = status.get("last_event") or {}
    if last.get("module") and last.get("module") != status.get("active_mode"):
        return "No material event yet", "Complete the current module action to update backend", "N/A"
    if status.get("last_emit_error"):
        return "Not ready", status.get("last_emit_error"), "N/A"
    result = status.get("last_backend_result") or {}
    effect = result.get("operational_effect") or {}
    signal = effect.get("signal") or {}
    intervention = effect.get("intervention") or {}
    if intervention.get("recommended_action"):
        decision = intervention.get("intervention_type", "AI RECOMMENDATION")
        action = intervention["recommended_action"]
    elif signal.get("signal_type"):
        decision = signal["signal_type"]
        action = "Operational state updated"
    elif result.get("delivery_status") == "DELIVERED":
        decision = "Decision applied"
        action = "Web dashboard updated"
    else:
        decision = "Waiting"
        action = "Run the module workflow"
    confidence = signal.get("confidence")
    return str(decision).replace("_", " "), str(action)[:52], f"{confidence:.0%}" if isinstance(confidence, (int, float)) else "N/A"


def _detection_lines(mode: str, status: dict) -> list[str]:
    analysis = status.get("latest_analysis") or {}
    detections = analysis.get("detections") or []
    qr = analysis.get("qr") or {}
    observations = analysis.get("tracking_observations") or []
    loading = analysis.get("loading") or {}
    hub = analysis.get("hub") or {}
    damage = analysis.get("damage") or {}
    last = status.get("last_event") or {}
    payload = last.get("payload") or {}
    if mode == "PACKAGE_QUALITY":
        top = detections[0] if detections else {}
        label = damage.get("label")
        confidence = float(damage.get("confidence") or 0)
        condition = label or ("READY TO ANALYZE" if top else "WAITING")
        quality = 97 if label == "NORMAL" else 61 if label == "DAMAGED" else 0
        severity = "Low" if label == "NORMAL" else "Medium" if label == "DAMAGED" else "Pending"
        recommendation = "Ready for dispatch" if label == "NORMAL" else "Manual inspection" if label == "DAMAGED" else "Press A to analyze"
        return [
            f"Package: {'Detected' if top else 'Waiting'}",
            f"Condition: {condition}",
            f"Confidence: {confidence:.0%}" if label else (f"Box confidence: {top.get('confidence', 0):.0%}" if top else "Confidence: N/A"),
            f"Severity: {severity}",
            f"Quality Score: {quality}/100" if quality else "Quality Score: pending",
            f"Recommendation: {recommendation}",
        ]
    if mode == "DISPATCH_VALIDATION":
        qr_payload = qr.get("payload") or {}
        return [
            f"Shipment: {qr_payload.get('shipment_id', 'Scan SHP-LOAD-001')}",
            f"Package: {qr_payload.get('package_id', '-')}",
            f"Expected Vehicle: {payload.get('expected_vehicle_id', 'VAN-021')}",
            f"Current Vehicle: {status.get('active_loading_context', {}).get('current_vehicle_id')}",
            f"Status: {payload.get('validation_result', 'WAITING')}",
            f"Dispatch: {payload.get('dispatch_state', 'PENDING')}",
        ]
    if mode == "LOADING_COMPLIANCE":
        loaded_ids = loading.get("loaded_track_ids", [])
        status_text = "OVER CAPACITY" if loading.get("status") == "BLOCKED" else "READY"
        return [
            f"Tracking: {status.get('configured_loading_tracking')} / {status.get('tracker_status')}",
            f"Detected Packages: {loading.get('loaded_packages', 0)}",
            f"Maximum: {loading.get('visual_capacity', 5)}",
            f"Status: {status_text}",
            f"Recommendation: {'Remove one package' if status_text == 'OVER CAPACITY' else 'Dispatch can proceed'}",
            f"Detected IDs: {', '.join(loaded_ids[:3]) if loaded_ids else 'show markers'}",
        ]
    track = (hub.get("track_states") or [{}])[-1]
    current = track.get("current_zone") or "NONE"
    previous = track.get("previous_zone") or "-"
    dwell = track.get("current_zone_dwell_min", hub.get("average_dwell_min", 0))
    return [
        f"Tracking: {status.get('configured_hub_tracking')} / {status.get('tracker_status')}",
        f"Current Zone: {current}",
        f"Previous Zone: {previous}",
        f"Time in Zone: {dwell} sim min",
        f"Transitions: {track.get('transition_count', 0)}",
        f"Congestion: {hub.get('congestion_level', 'LOW')} / Occupancy {sum((hub.get('zone_counts') or {}).values())}",
    ]



def _pt(point, w, h):
    x, y = point
    return int(x * w if 0 <= x <= 1 else x), int(y * h if 0 <= y <= 1 else y)


def _draw_poly(cv2, frame, points, color, label=None):
    import numpy as np
    h, w = frame.shape[:2]
    pts = np.array([_pt(p, w, h) for p in points], dtype=np.int32)
    cv2.polylines(frame, [pts], True, color, 2)
    if label:
        x, y = pts[0]
        _text(cv2, frame, label, int(x) + 4, int(y) + 18, .5, color, 2)


def _draw_operational_guides(cv2, frame, status):
    mode = status.get("active_mode")
    analysis = status.get("latest_analysis") or {}
    if mode == "LOADING_COMPLIANCE":
        roi = (analysis.get("loading") or {}).get("roi") or {}
        if roi.get("roi_polygon"):
            _draw_poly(cv2, frame, roi["roi_polygon"], (14, 165, 233), "LOADING ROI")
        if roi.get("entry_line"):
            h, w = frame.shape[:2]
            p1, p2 = [_pt(p, w, h) for p in roi["entry_line"]]
            cv2.line(frame, p1, p2, (34, 197, 94), 3)
            _text(cv2, frame, "ENTRY", p1[0] + 4, p1[1] + 24, .55, (34, 197, 94), 2)
        if roi.get("exit_line"):
            h, w = frame.shape[:2]
            p1, p2 = [_pt(p, w, h) for p in roi["exit_line"]]
            cv2.line(frame, p1, p2, (239, 68, 68), 2)
            _text(cv2, frame, "EXIT", p1[0] + 4, p1[1] + 24, .55, (239, 68, 68), 2)
    if mode == "HUB_VISION":
        for zone in (analysis.get("hub") or {}).get("zones") or []:
            colors = {"INCOMING": (34, 197, 94), "PROCESSING": (245, 158, 11), "OUTGOING": (59, 130, 246)}
            _draw_poly(cv2, frame, zone.get("polygon") or [], colors.get(zone.get("zone_id"), (245, 158, 11)), zone.get("zone_id"))
    return frame

def _draw_analysis(cv2, frame, status):
    analysis = status.get("latest_analysis") or {}
    frame = _draw_operational_guides(cv2, frame, status)
    for item in analysis.get("detections") or []:
        x1, y1, x2, y2 = [int(v) for v in item["bbox"]]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (34, 197, 94), 2)
        _text(cv2, frame, f"{item['raw_class']} {item['confidence']:.0%}", x1, max(20, y1 - 8), .55, (34, 197, 94), 2)
    for marker in analysis.get("tracking_observations") or []:
        x1, y1, x2, y2 = [int(v) for v in marker["bbox"]]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (59, 130, 246), 2)
        _text(cv2, frame, marker["track_id"], x1, max(20, y1 - 8), .55, (59, 130, 246), 2)
    qr = analysis.get("qr")
    if qr and qr.get("points"):
        pts = qr["points"][0] if len(qr["points"]) == 1 else qr["points"]
        for i in range(len(pts)):
            p1 = tuple(int(v) for v in pts[i])
            p2 = tuple(int(v) for v in pts[(i + 1) % len(pts)])
            cv2.line(frame, p1, p2, (245, 158, 11), 2)
    return frame


def _annotate(cv2, frame):
    import numpy as np

    status = runtime.status()
    mode = status["active_mode"]
    canvas = np.full((720, 1280, 3), 255, dtype="uint8")
    cv2.rectangle(canvas, (0, 0), (1280, 720), (241, 245, 249), -1)
    cv2.rectangle(canvas, (16, 16), (1264, 704), (15, 23, 42), 2)
    cv2.rectangle(canvas, (16, 16), (1264, 72), (15, 23, 42), -1)
    _text(cv2, canvas, "B.A.L.O.N Visual Sensor", 34, 52, .82, (255, 255, 255), 2)
    cam_dot = (34, 197, 94) if status["camera_status"] == "ONLINE" else (239, 68, 68)
    cv2.circle(canvas, (1108, 44), 8, cam_dot, -1)
    _text(cv2, canvas, f"Mode: {MODE_LABELS.get(mode, mode)}", 620, 50, .62, (226, 232, 240), 1)
    _text(cv2, canvas, f"Camera {status['camera_status']}", 1122, 50, .62, (226, 232, 240), 1)

    video_x1, video_y1, video_x2, video_y2 = 34, 92, 855, 594
    cv2.rectangle(canvas, (video_x1, video_y1), (video_x2, video_y2), (15, 23, 42), -1)
    if frame is not None:
        frame = _draw_analysis(cv2, frame.copy(), status)
        target_w, target_h = video_x2 - video_x1, video_y2 - video_y1
        h, w = frame.shape[:2]
        scale = min(target_w / max(w, 1), target_h / max(h, 1))
        resized = cv2.resize(frame, (int(w * scale), int(h * scale)))
        rh, rw = resized.shape[:2]
        ox = video_x1 + (target_w - rw) // 2
        oy = video_y1 + (target_h - rh) // 2
        canvas[oy:oy + rh, ox:ox + rw] = resized
    else:
        _text(cv2, canvas, f"Camera unavailable: {status['camera_error']}", video_x1 + 30, video_y1 + 240, .72, (248, 113, 113), 2)

    _panel(cv2, canvas, 880, 92, 1238, 292, "DETECTION")
    for i, line in enumerate(_detection_lines(mode, status)):
        _text(cv2, canvas, line, 900, 140 + i * 32, .56)

    _panel(cv2, canvas, 880, 312, 1238, 498, "BACKEND RESULT")
    decision, action, conf = _backend_decision(status)
    _text(cv2, canvas, decision[:34], 900, 362, .58, (15, 23, 42), 2)
    _text(cv2, canvas, action, 900, 398, .5, (71, 85, 105), 1)
    _text(cv2, canvas, f"Backend confidence: {conf}", 900, 434, .52, (71, 85, 105), 1)
    delivery_label = "Dashboard updated" if status["delivery_status"] == "DELIVERED" else status["delivery_status"]
    _text(cv2, canvas, delivery_label, 900, 470, .52, (22, 163, 74) if status["delivery_status"] == "DELIVERED" else (202, 138, 4), 2)

    _panel(cv2, canvas, 880, 518, 1238, 594, "AI RECOMMENDATION")
    last = status.get("last_event") or {}
    rec = (last.get("payload") or {}).get("dispatch_state") or str(last.get("event_type", "No material event yet")).replace("_", " ")
    _text(cv2, canvas, rec[:38], 900, 566, .54)

    cv2.rectangle(canvas, (16, 616), (1264, 704), (15, 23, 42), -1)
    delivered_dot = (34, 197, 94) if status["delivery_status"] == "DELIVERED" else (245, 158, 11) if status["delivery_status"] == "QUEUED" else (148, 163, 184)
    cv2.circle(canvas, (626, 648), 7, delivered_dot, -1)
    footer = f"FPS {status['camera_fps']:.1f} | Latency {status['latency_ms']:.0f} ms | Event {status['delivery_status']} | Queue {status['pending_events']} | Backend {'ON' if status['backend_enabled'] else 'OFF'}"
    _text(cv2, canvas, footer, 36, 654, .62, (226, 232, 240), 1)
    _text(cv2, canvas, "[1 Quality] [2 Dispatch] [3 Loading] [4 Hub] [A Analyze] [E Emit] [R Reset] [F1/F2 Context] [B Backend] [Q Quit]", 36, 688, .56, (226, 232, 240), 1)
    return canvas


def run_desktop(camera_index: int = 0, source_video: str | None = None) -> None:
    import cv2  # type: ignore
    import numpy as np

    runtime.camera.configure(camera_index=camera_index, source_video=source_video)
    runtime.camera.start()
    window = "B.A.L.O.N Visual Sensor"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, 1280, 720)
    try:
        while True:
            frame = runtime.camera.frame()
            if frame is None:
                frame = np.zeros((480, 640, 3), dtype="uint8")
            else:
                runtime.analyze_frame(frame)
            cv2.imshow(window, _annotate(cv2, frame))
            key = cv2.waitKey(1) & 0xFF
            if key in MODE_KEYS:
                runtime.mode = MODE_KEYS[key]
            elif key in {ord("q"), 27}:
                break
            elif key == ord("s"):
                runtime.camera.start()
            elif key == ord("p"):
                runtime.camera.stop()
            elif key == ord("r"):
                runtime.reset_active_module()
            elif key == ord("b"):
                runtime.backend_enabled = not runtime.backend_enabled
            elif key == ord("a"):
                runtime.analyze_damage(frame)
            elif key == ord("e"):
                runtime.emit_material_event()
            elif key == 0x70:  # F1 on Windows OpenCV
                runtime.set_loading_context("CORRECT")
            elif key == 0x71:  # F2
                runtime.set_loading_context("WRONG")
            elif key == ord("c"):
                runtime.set_loading_context("CORRECT")
            elif key == ord("w"):
                runtime.set_loading_context("WRONG")
    finally:
        runtime.camera.stop()
        runtime.event_client.stop()
        cv2.destroyAllWindows()
