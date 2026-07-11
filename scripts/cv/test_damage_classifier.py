from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/cv/damage_detector/v1/damage_detector.pth")
    parser.add_argument("--image")
    parser.add_argument("--camera-index", type=int, default=0)
    args = parser.parse_args()

    import cv2  # type: ignore
    from cv_worker.detectors.damage_classifier import PyTorchDamageClassifier

    model_path = Path(args.model)
    if not model_path.is_absolute():
        model_path = ROOT / model_path
    classifier = PyTorchDamageClassifier(model_path)
    if args.image:
        image = cv2.imread(str(Path(args.image)))
        if image is None:
            raise SystemExit(f"Could not read image {args.image}")
    else:
        cap = cv2.VideoCapture(args.camera_index)
        ok, image = cap.read()
        cap.release()
        if not ok:
            raise SystemExit(f"Could not capture image from camera {args.camera_index}")
    result = classifier.predict(image)
    print("PACKAGE CONDITION CLASSIFICATION")
    print(result)


if __name__ == "__main__":
    main()
