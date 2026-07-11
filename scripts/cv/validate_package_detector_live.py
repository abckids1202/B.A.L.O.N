from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/cv/package_detector/v1/best.pt")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--duration", type=float, default=10)
    args = parser.parse_args()

    import cv2  # type: ignore
    from ultralytics import YOLO  # type: ignore

    model_path = Path(args.model)
    if not model_path.is_absolute():
        model_path = ROOT / model_path
    model = YOLO(str(model_path))
    cap = cv2.VideoCapture(args.camera_index)
    if not cap.isOpened():
        raise SystemExit(f"Camera index {args.camera_index} did not open")
    out_dir = ROOT / "outputs" / "cv" / "package_validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = 0
    detected = 0
    confidences = []
    classes = {}
    started = time.time()
    sample_written = 0
    while time.time() - started < args.duration:
        ok, frame = cap.read()
        if not ok:
            continue
        frames += 1
        result = model.predict(frame, conf=args.confidence, verbose=False)[0]
        annotated = result.plot()
        boxes = result.boxes
        if boxes is not None and len(boxes):
            detected += 1
            for box in boxes:
                cls = int(box.cls[0])
                name = result.names.get(cls, f"class_{cls}")
                classes[name] = classes.get(name, 0) + 1
                confidences.append(float(box.conf[0]))
            if sample_written < 5:
                cv2.imwrite(str(out_dir / f"sample_{sample_written + 1}.jpg"), annotated)
                sample_written += 1
        cv2.imshow("Package detector validation", annotated)
        if cv2.waitKey(1) & 0xFF in {27, ord("q")}:
            break
    cap.release()
    cv2.destroyAllWindows()
    report = {
        "model": str(model_path),
        "frames_analyzed": frames,
        "frames_with_detections": detected,
        "detection_frame_ratio": round(detected / frames, 3) if frames else 0,
        "classes": classes,
        "average_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
        "acceptance_hint": "PASS if a real package was visible and detection_frame_ratio >= 0.5",
    }
    report_path = ROOT / "outputs" / "cv" / "package_model_physical_validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
