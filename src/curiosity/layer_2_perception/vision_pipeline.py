"""Layer 2: Perception Module for Curiosity AI.

Integrates:
1. YOLOv11 Real-Time Object Detector (Ultralytics) for localization & multi-object counting
2. ResNet-50 Pretrained Backbone (ImageNet-1K) for high-level scene taxonomy
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional
from PIL import Image
import torch

from src.curiosity.layer_0_core.contracts import (
    DetectedObject,
    ImageNetPrediction,
    PerceptionResult
)
from src.curiosity.layer_0_core.config import (
    DEVICE,
    RESNET_TOP_K,
    YOLO_CONFIDENCE_THRESHOLD,
    YOLO_MODEL_NAME
)

logger = logging.getLogger("curiosity.layer_2")


class YOLO11Detector:
    """YOLOv11 real-time object detector."""

    def __init__(self, model_name: str = YOLO_MODEL_NAME):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from ultralytics import YOLO
                self._model = YOLO(self.model_name)
                logger.info(f"[Layer 2] YOLO11 ({self.model_name}) loaded successfully.")
            except Exception as exc:
                logger.warning(f"[Layer 2] YOLO11 model load warning ({exc}), trying fallback yolov8n.pt...")
                try:
                    from ultralytics import YOLO
                    self._model = YOLO("yolov8n.pt")
                except Exception as inner_exc:
                    logger.error(f"[Layer 2] Failed to initialize YOLO: {inner_exc}")
                    self._model = None

    def detect(self, image: Image.Image, conf_threshold: float = YOLO_CONFIDENCE_THRESHOLD) -> List[DetectedObject]:
        """Detect objects using YOLOv11 and return detected objects."""
        self._load_model()
        if self._model is None:
            return []

        try:
            rgb_image = image.convert("RGB")
            results = self._model(rgb_image, conf=conf_threshold, verbose=False)
            if not results:
                return []

            detected_objects: List[DetectedObject] = []
            first_res = results[0]
            boxes = first_res.boxes
            names = first_res.names

            if boxes is not None:
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    label = names.get(cls_id, f"class_{cls_id}")
                    conf = float(box.conf[0].item())
                    xyxy = [float(c) for c in box.xyxy[0].tolist()]

                    detected_objects.append(
                        DetectedObject(
                            label=label,
                            confidence=conf,
                            box=xyxy
                        )
                    )

            return detected_objects
        except Exception as exc:
            logger.warning(f"[Layer 2] YOLO11 detection error: {exc}")
            return []


class ResNetClassifier:
    """ResNet-50 classifier on ImageNet (1000 categories)."""

    def __init__(self, device: torch.device = DEVICE):
        self.device = device
        self._model = None
        self._transforms = None
        self._categories = None

    def _load_model(self):
        if self._model is None:
            try:
                from torchvision.models import ResNet50_Weights, resnet50
                weights = ResNet50_Weights.DEFAULT
                self._transforms = weights.transforms()
                self._categories = weights.meta.get("categories", [])
                
                model = resnet50(weights=weights)
                model.eval()
                self._model = model.to(self.device)
                logger.info(f"[Layer 2] ResNet-50 initialized on {self.device}.")
            except Exception as exc:
                logger.warning(f"[Layer 2] ResNet-50 weights load notice: {exc}")
                self._model = None

    def predict(self, image: Image.Image, top_k: int = RESNET_TOP_K) -> List[ImageNetPrediction]:
        """Classify image into top-k ImageNet categories with confidence scores."""
        self._load_model()
        if self._model is None or not self._categories:
            return []

        try:
            rgb_image = image.convert("RGB")
            tensor = self._transforms(rgb_image).unsqueeze(0).to(self.device)

            with torch.inference_mode():
                logits = self._model(tensor)
                probs = torch.softmax(logits, dim=1)[0]
                topk_vals, topk_indices = torch.topk(probs, min(top_k, len(self._categories)))

            predictions: List[ImageNetPrediction] = []
            for val, idx in zip(topk_vals, topk_indices):
                label = self._categories[idx.item()]
                clean_label = label.split(",")[0].strip()
                predictions.append(ImageNetPrediction(label=clean_label, confidence=float(val.item())))

            return predictions
        except Exception as exc:
            logger.warning(f"[Layer 2] ResNet-50 prediction notice: {exc}")
            return []


class VisionPerceptionPipeline:
    """Unified Layer 2 Vision Pipeline executing YOLOv11 and ResNet-50."""

    _instance: Optional[VisionPerceptionPipeline] = None

    def __init__(self):
        self.yolo_detector = YOLO11Detector()
        self.resnet_classifier = ResNetClassifier()

    @classmethod
    def get_instance(cls) -> VisionPerceptionPipeline:
        if cls._instance is None:
            cls._instance = VisionPerceptionPipeline()
        return cls._instance

    def process(self, image: Optional[Image.Image]) -> PerceptionResult:
        """Run YOLOv11 and ResNet-50 on the input image."""
        t0 = time.time()
        result = PerceptionResult()

        if image is None:
            result.duration_s = time.time() - t0
            return result

        # 1. Run YOLOv11 Object Detection
        detected = self.yolo_detector.detect(image, conf_threshold=YOLO_CONFIDENCE_THRESHOLD)
        result.yolo_objects = detected

        counts: Dict[str, int] = {}
        for obj in detected:
            counts[obj.label] = counts.get(obj.label, 0) + 1
        result.yolo_counts = counts

        if detected:
            items_str = []
            for label, count in counts.items():
                plural = f"{count} {label}s" if count > 1 else f"1 {label}"
                best_conf = max(o.confidence for o in detected if o.label == label)
                items_str.append(f"{plural} ({best_conf * 100:.1f}% confidence)")
            result.yolo_summary = f"Detected {len(detected)} object(s): " + ", ".join(items_str) + "."
        else:
            result.yolo_summary = "No standard foreground objects detected."

        # 2. Run ResNet-50 ImageNet Classification
        top_preds = self.resnet_classifier.predict(image, top_k=RESNET_TOP_K)
        result.resnet_top5 = top_preds
        if top_preds:
            result.resnet_top1 = top_preds[0].label
            top_strs = [f"{p.label} ({p.confidence * 100:.1f}%)" for p in top_preds[:3]]
            result.resnet_summary = f"Top ImageNet predictions: {', '.join(top_strs)}."
        else:
            result.resnet_summary = "Scene classification inconclusive."

        result.duration_s = time.time() - t0
        return result
