from __future__ import annotations

import hashlib
import random


CLASSES = ["small_box", "medium_box", "large_box", "delivery_bag", "loose_package", "strap", "motorcycle", "van_loading_area"]


def validate_image(filename: str, content: bytes, max_mb: int = 8) -> None:
    if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise ValueError("Unsupported image type. Use JPG, JPEG, or PNG.")
    if len(content) > max_mb * 1024 * 1024:
        raise ValueError("Image exceeds configured upload size.")
    if not content:
        raise ValueError("Image is empty.")


def demo_detections(content: bytes) -> dict:
    digest = hashlib.sha256(content).hexdigest()
    rng = random.Random(int(digest[:8], 16))
    count = rng.randint(4, 8)
    detections = []
    for i in range(count):
        cls = rng.choice(CLASSES)
        detections.append({
            "class_name": cls,
            "confidence": round(rng.uniform(0.58, 0.94), 3),
            "bbox": [rng.randint(20, 280), rng.randint(20, 220), rng.randint(300, 560), rng.randint(240, 420)],
        })
    classes = [d["class_name"] for d in detections]
    score = 92
    warnings = []
    if "loose_package" in classes:
        score -= 18
        warnings.append("Loose Package")
    if "strap" not in classes:
        score -= 14
        warnings.append("No Strap Detected")
    if classes.count("large_box") >= 2:
        score -= 8
        warnings.append("High Load Pattern")
    score = max(score, 35)
    status = "Warning" if warnings else "Normal"
    return {
        "detections": detections,
        "compliance_score": score,
        "status": status,
        "warnings": warnings or ["No major loading warning."],
        "image_hash": digest,
        "model_source": "Deterministic Demo Detection Mode",
        "is_demo": True,
        "disclosure": "Demo detections are deterministic synthetic results and are not real YOLO inference.",
    }
