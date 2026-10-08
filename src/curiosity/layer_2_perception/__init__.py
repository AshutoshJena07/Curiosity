"""Layer 2 Perception module exports."""

from src.curiosity.layer_2_perception.vision_pipeline import (
    YOLO11Detector,
    ResNetClassifier,
    VisionPerceptionPipeline
)

__all__ = ["YOLO11Detector", "ResNetClassifier", "VisionPerceptionPipeline"]
