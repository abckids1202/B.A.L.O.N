from __future__ import annotations

import time
from pathlib import Path

import numpy as np


class PyTorchDamageClassifier:
    labels = ["NORMAL", "DAMAGED"]

    def __init__(self, checkpoint_path: Path, device: str = "cpu") -> None:
        import torch
        from torchvision import models

        self.device_name = device
        self.torch = torch
        try:
            self.model = models.resnet18(weights=None)
        except TypeError:
            self.model = models.resnet18(pretrained=False)
        self.model.fc = torch.nn.Linear(self.model.fc.in_features, 2)
        checkpoint = torch.load(str(checkpoint_path), map_location="cpu")
        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            checkpoint = checkpoint["model_state_dict"]
        self.model.load_state_dict(checkpoint)
        self.model.eval()

    def predict(self, image_bgr: np.ndarray) -> dict:
        import cv2  # type: ignore
        import torch
        from PIL import Image
        from torchvision import transforms

        started = time.perf_counter()
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        tensor = transform(pil).unsqueeze(0)
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
        index = int(probs.argmax())
        return {
            "label": self.labels[index],
            "confidence": float(probs[index]),
            "processing_time_ms": round((time.perf_counter() - started) * 1000, 2),
            "model_type": "PYTORCH_RESNET18_BINARY_CLASSIFIER",
        }
