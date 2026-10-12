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

            # Apply Universal Class-Wise Non-Maximum Suppression (NMS) & Containment Filter
            return self._apply_nms(detected_objects)
        except Exception as exc:
            logger.warning(f"[Layer 2] YOLO11 detection error: {exc}")
            return []

    @staticmethod
    def _apply_nms(objects: List[DetectedObject], iou_thresh: float = 0.42, containment_thresh: float = 0.62) -> List[DetectedObject]:
        """Universally deduplicates overlapping boxes of the same class across all media."""
        if len(objects) <= 1:
            return objects

        # Group by class label
        by_class: Dict[str, List[DetectedObject]] = {}
        for obj in objects:
            by_class.setdefault(obj.label.lower(), []).append(obj)

        kept: List[DetectedObject] = []
        for label, group in by_class.items():
            # Sort by confidence descending
            sorted_objs = sorted(group, key=lambda o: o.confidence, reverse=True)
            class_kept: List[DetectedObject] = []

            for candidate in sorted_objs:
                b1 = candidate.box
                a1 = max(1.0, (b1[2] - b1[0]) * (b1[3] - b1[1]))
                is_duplicate = False

                for existing in class_kept:
                    b2 = existing.box
                    a2 = max(1.0, (b2[2] - b2[0]) * (b2[3] - b2[1]))

                    ix1 = max(b1[0], b2[0])
                    iy1 = max(b1[1], b2[1])
                    ix2 = min(b1[2], b2[2])
                    iy2 = min(b1[3], b2[3])

                    inter_w = max(0.0, ix2 - ix1)
                    inter_h = max(0.0, iy2 - iy1)
                    inter_area = inter_w * inter_h

                    iou = inter_area / (a1 + a2 - inter_area) if (a1 + a2 - inter_area) > 0 else 0
                    containment = inter_area / min(a1, a2)

                    # Same physical entity if high IoU or one box is substantially nested within the other
                    if label == "person":
                        if iou >= 0.45 or containment >= 0.52:
                            is_duplicate = True
                            break
                    elif iou >= iou_thresh or containment >= containment_thresh:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    class_kept.append(candidate)

            kept.extend(class_kept)

        # Restore original confidence ordering
        kept.sort(key=lambda o: o.confidence, reverse=True)
        return kept


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

    def process(self, image: Optional[Image.Image], prompt: str = "") -> PerceptionResult:
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

        # 2B. Wildlife & Multi-Species Animal Intelligence Engine
        try:
            from src.curiosity.layer_2_perception.wildlife_detector import WildlifeFaunaEngine
            detected = WildlifeFaunaEngine.enhance_detections(
                image=image,
                initial_detected=detected,
                resnet_classifier=self.resnet_classifier,
                yolo_detector=self.yolo_detector,
                prompt=prompt
            )
            result.yolo_objects = detected

            # Recompute counts with verified species
            counts = {}
            for obj in detected:
                counts[obj.label] = counts.get(obj.label, 0) + 1
            result.yolo_counts = counts

            if detected:
                items_str = []
                for label, count in counts.items():
                    plural = f"{count} {label}s" if count > 1 and not (label.endswith('s') or label.endswith('sheep')) else f"1 {label}"
                    best_conf = max(o.confidence for o in detected if o.label == label)
                    items_str.append(f"{plural} ({best_conf * 100:.1f}% confidence)")
                result.yolo_summary = f"Detected {len(detected)} object(s): " + ", ".join(items_str) + "."
        except Exception as wild_err:
            logger.warning(f"[Layer 2] Wildlife detection notice: {wild_err}")

        # 3. Run Traffic & Safety Violation Engine (Helmet, Triple Riding, Phone Distraction)
        try:
            from src.curiosity.layer_2_perception.traffic_violation_detector import TrafficRuleViolationEngine
            violations, traffic_summary = TrafficRuleViolationEngine.analyze(image, detected, prompt=prompt)
            result.traffic_violations = violations
            result.traffic_summary = traffic_summary
        except Exception as traffic_err:
            logger.warning(f"[Layer 2] Traffic rule evaluation notice: {traffic_err}")

        # 4. Generate Visual Detection & Violation Overlay Image
        try:
            from src.curiosity.layer_2_perception.image_annotator import VisualDetectionAnnotator
            low_p = (prompt or "").lower()
            explicit_traffic = any(k in low_p for k in [
                "helmet", "triple", "tripling", "3seater", "3 seater", "3-seater",
                "challan", "violation", "fine", "penalty", "traffic rule", "rule break", "mv act"
            ])
            counts = result.yolo_counts or {}
            has_triple_riding = any(v.rider_count >= 3 for v in (result.traffic_violations or []))
            is_general_street_with_animals = ("cow" in counts or "ox" in counts) and counts.get("car", 0) >= 1
            
            show_traffic_overlay = explicit_traffic or has_triple_riding or (bool(result.traffic_violations) and not is_general_street_with_animals and ("motorcycle" in counts or "bicycle" in counts))
            overlay_violations = result.traffic_violations if show_traffic_overlay else None
            annotated_url = VisualDetectionAnnotator.annotate(
                image=image,
                detected_objects=detected,
                traffic_violations=overlay_violations
            )
            result.annotated_image = annotated_url
        except Exception as anno_err:
            logger.warning(f"[Layer 2] Visual annotation overlay notice: {anno_err}")

        # 5. Run AI-Generated & Deepfake Authenticity Forensics
        try:
            from src.curiosity.layer_2_perception.authenticity_detector import ImageAuthenticityEngine
            result.authenticity = ImageAuthenticityEngine.evaluate(image)
        except Exception as auth_err:
            logger.warning(f"[Layer 2] Authenticity forensics notice: {auth_err}")

        result.duration_s = time.time() - t0
        return result
