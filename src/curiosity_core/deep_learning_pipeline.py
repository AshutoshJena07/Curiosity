"""Deep Learning Vision Pipeline for Image Recognition & Analysis.

Incorporates industry-standard Deep Learning backbones:
1. YOLO (YOLOv8 by Ultralytics): Real-time Object Detection, Localization, and Count Extraction.
2. ResNet-50 (Deep Residual Network): ImageNet-1K (1000-class) Fine-grained Classification.
3. Multimodal Context Fusion: Blends deep learning outputs into the multimodal summarizer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from PIL import Image
import torch

logger = logging.getLogger("Curiosity.DeepLearning")


@dataclass
class DetectedObject:
    """A detected object bounding box and class prediction from YOLO."""
    label: str
    confidence: float
    box: List[float] = field(default_factory=list)  # [x1, y1, x2, y2]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "percentage": f"{self.confidence * 100:.1f}%",
            "box": [round(coord, 2) for coord in self.box]
        }


@dataclass
class ImageNetPrediction:
    """An ImageNet category prediction from ResNet-50."""
    label: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "percentage": f"{self.confidence * 100:.1f}%"
        }


@dataclass
class DeepLearningAnalysisResult:
    """Consolidated Deep Learning output combining YOLO and ResNet-50 ImageNet."""
    # YOLO Object Detection
    yolo_objects: List[DetectedObject] = field(default_factory=list)
    yolo_counts: Dict[str, int] = field(default_factory=dict)
    yolo_summary: str = ""

    # ResNet ImageNet-1K Classification
    resnet_top5: List[ImageNetPrediction] = field(default_factory=list)
    resnet_top1_label: str = ""
    resnet_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "yolo": {
                "detected_objects": [obj.to_dict() for obj in self.yolo_objects],
                "object_counts": self.yolo_counts,
                "total_objects": len(self.yolo_objects),
                "summary": self.yolo_summary,
            },
            "resnet_imagenet": {
                "top_prediction": self.resnet_top1_label,
                "top5_predictions": [p.to_dict() for p in self.resnet_top5],
                "summary": self.resnet_summary,
            }
        }

    def format_context_for_prompt(self) -> str:
        """Format the DL results into a high-signal prompt context for the summarizer."""
        lines = []
        if self.yolo_summary:
            lines.append(f"[YOLO Object Detection]: {self.yolo_summary}")
        if self.resnet_summary:
            lines.append(f"[ResNet-50 ImageNet Classification]: {self.resnet_summary}")
        return "\n".join(lines)


class ResNetImageNetClassifier:
    """Pretrained ResNet-50 classifier on ImageNet (1000 categories)."""

    def __init__(self, device: Optional[torch.device] = None):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model = None
        self._transforms = None
        self._categories = None

    def _load_model(self):
        if self._model is None:
            try:
                from torchvision.models import resnet50, ResNet50_Weights
                weights = ResNet50_Weights.DEFAULT
                self._transforms = weights.transforms()
                self._categories = weights.meta.get("categories", [])
                
                model = resnet50(weights=weights)
                model.eval()
                self._model = model.to(self.device)
                print(f"[DeepLearning] ResNet-50 (ImageNet-1K) successfully initialized on {self.device}.")
            except Exception as exc:
                logger.error(f"Failed to load ResNet-50 weights: {exc}")
                raise

    def predict(self, image: Image.Image, top_k: int = 5) -> List[ImageNetPrediction]:
        """Classify image into top-k ImageNet categories with confidence scores."""
        self._load_model()
        if self._model is None or not self._categories:
            return []

        rgb_image = image.convert("RGB")
        tensor = self._transforms(rgb_image).unsqueeze(0).to(self.device)

        with torch.inference_mode():
            logits = self._model(tensor)
            probs = torch.softmax(logits, dim=1)[0]
            topk_vals, topk_indices = torch.topk(probs, min(top_k, len(self._categories)))

        predictions: List[ImageNetPrediction] = []
        for val, idx in zip(topk_vals, topk_indices):
            label = self._categories[idx.item()]
            # Clean up comma-separated synonyms (e.g. "sports car, sport car" -> "sports car")
            clean_label = label.split(",")[0].strip()
            predictions.append(ImageNetPrediction(label=clean_label, confidence=float(val.item())))

        return predictions


class YOLOObjectDetector:
    """YOLOv8 real-time object detector for multi-class localization and counting."""

    def __init__(self, model_name: str = "yolov8n.pt"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from ultralytics import YOLO
                self._model = YOLO(self.model_name)
                print(f"[DeepLearning] YOLO ({self.model_name}) successfully initialized.")
            except Exception as exc:
                logger.error(f"Failed to load YOLO model: {exc}")
                raise

    def detect(self, image: Image.Image, conf_threshold: float = 0.25) -> List[DetectedObject]:
        """Run YOLO object detection and return detected bounding boxes and labels."""
        self._load_model()
        if self._model is None:
            return []

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


class DeepLearningVisionPipeline:
    """Unified pipeline executing both YOLO Object Detection and ResNet ImageNet Classification."""

    def __init__(self):
        self.resnet_classifier = ResNetImageNetClassifier()
        self.yolo_detector = YOLOObjectDetector(model_name="yolov8n.pt")

    def analyze(self, image: Image.Image) -> DeepLearningAnalysisResult:
        """Run deep learning analysis on an image using YOLO and ResNet-50."""
        result = DeepLearningAnalysisResult()

        # 1. Run YOLO Object Detection
        try:
            detected = self.yolo_detector.detect(image, conf_threshold=0.25)
            result.yolo_objects = detected

            # Aggregate counts per class
            counts: Dict[str, int] = {}
            for obj in detected:
                counts[obj.label] = counts.get(obj.label, 0) + 1
            result.yolo_counts = counts

            if detected:
                items_str = []
                for label, count in counts.items():
                    plural = f"{count} {label}s" if count > 1 else f"1 {label}"
                    # Find highest confidence for this class
                    best_conf = max(o.confidence for o in detected if o.label == label)
                    items_str.append(f"{plural} ({best_conf * 100:.1f}% confidence)")
                result.yolo_summary = f"Detected {len(detected)} object(s): " + ", ".join(items_str) + "."
            else:
                result.yolo_summary = "No standard foreground COCO objects detected at confidence threshold >= 0.25."
        except Exception as exc:
            logger.warning(f"YOLO detection skipped or encountered error: {exc}")
            result.yolo_summary = "YOLO object detection unavailable."

        # 2. Run ResNet-50 ImageNet Classification
        try:
            top5 = self.resnet_classifier.predict(image, top_k=5)
            result.resnet_top5 = top5
            if top5:
                result.resnet_top1_label = top5[0].label
                top_strs = [f"{p.label} ({p.confidence * 100:.1f}%)" for p in top5[:3]]
                result.resnet_summary = f"Top ImageNet predictions: {', '.join(top_strs)}."
            else:
                result.resnet_summary = "ImageNet classification yielded no confident classes."
        except Exception as exc:
            logger.warning(f"ResNet ImageNet classification skipped or encountered error: {exc}")
            result.resnet_summary = "ResNet-50 ImageNet classification unavailable."

        return result


# Global Singleton instance
_PIPELINE_INSTANCE: Optional[DeepLearningVisionPipeline] = None


def get_dl_pipeline() -> DeepLearningVisionPipeline:
    """Obtain or initialize the global Deep Learning Vision Pipeline singleton."""
    global _PIPELINE_INSTANCE
    if _PIPELINE_INSTANCE is None:
        _PIPELINE_INSTANCE = DeepLearningVisionPipeline()
    return _PIPELINE_INSTANCE
