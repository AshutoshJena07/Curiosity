"""Layer 0: Core contracts, data transfer models, and schemas for Curiosity AI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MediaCategory(str, Enum):
    VISUAL_IMAGE = "visual_image"
    PDF_DOCUMENT = "pdf_document"
    OFFICE_DOCUMENT = "office_document"
    VIDEO = "video_media"
    AUDIO = "audio_media"
    TEXT_ONLY = "text_only"
    UNKNOWN = "unknown"


@dataclass
class MediaPayload:
    """Raw input payload received from HTTP upload or client."""
    file_bytes: Optional[bytes] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None
    user_prompt: str = ""
    history: List[Dict[str, str]] = field(default_factory=list)
    user_name: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class DetectedObject:
    """YOLOv11 detected object bounding box and confidence."""
    label: str
    confidence: float
    box: List[float]  # [x1, y1, x2, y2]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "box": [round(c, 2) for c in self.box]
        }


@dataclass
class ImageNetPrediction:
    """ResNet-50 taxonomic prediction."""
    label: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "confidence": round(self.confidence, 4)
        }


@dataclass
class GroundedEvidence:
    """Evidence span linking an observation to image coordinates or text snippets."""
    claim: str
    source_type: str  # 'yolo11', 'easyocr', 'pymupdf', 'resnet50'
    confidence: float
    bbox: Optional[List[float]] = None
    text_snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "claim": self.claim,
            "source_type": self.source_type,
            "confidence": round(self.confidence, 4)
        }
        if self.bbox is not None:
            res["bbox"] = [round(c, 2) for c in self.bbox]
        if self.text_snippet:
            res["text_snippet"] = self.text_snippet[:200]
        return res


@dataclass
class IngestionResult:
    """Result from Layer 1 Ingestion."""
    category: MediaCategory
    filename: str
    extension: str
    mime_type: str
    file_size: int
    is_document: bool
    is_visual: bool
    is_empty: bool
    description: str
    image: Optional[Any] = None  # PIL.Image if visual
    pdf_page_count: int = 0
    pdf_raster_images: List[Any] = field(default_factory=list)
    quality_score: float = 1.0  # 0.0 to 1.0 (Laplacian blur / contrast)


@dataclass
class TrafficViolation:
    """Traffic and Road Safety Rule Violation record."""
    violation_type: str         # "Triple Riding", "No Helmet (Rider)", "No Helmet (Pillion)", "Phone Use"
    rule_code: str              # "Section 128, MV Act", "Section 129, MV Act", "Section 184(c), MV Act"
    severity: str               # "CRITICAL", "HIGH", "MEDIUM"
    confidence: float           # 0.0 to 1.0
    description: str            # Detailed observation
    penalty: str                # Legal fine / penalty description
    bbox: Optional[List[float]] = None
    vehicle_bbox: Optional[List[float]] = None
    rider_count: int = 1
    helmets_detected: int = 0
    helmets_missing: int = 0

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "violation_type": self.violation_type,
            "rule_code": self.rule_code,
            "severity": self.severity,
            "confidence": round(self.confidence, 4),
            "description": self.description,
            "penalty": self.penalty,
            "rider_count": self.rider_count,
            "helmets_detected": self.helmets_detected,
            "helmets_missing": self.helmets_missing
        }
        if self.bbox:
            res["bbox"] = [round(c, 2) for c in self.bbox]
        if self.vehicle_bbox:
            res["vehicle_bbox"] = [round(c, 2) for c in self.vehicle_bbox]
        return res


@dataclass
class AuthenticityResult:
    """Forensic evaluation of AI generation or deepfake probability."""
    is_ai_generated: bool
    verdict: str  # "AI Generated / Synthetic", "Authentic Camera Image", "Suspected Manipulation"
    ai_probability: float  # 0.0 to 1.0
    authenticity_score: float  # 0.0 to 100.0%
    confidence_level: str  # "High Confidence", "Moderate Confidence", "Heuristic Assessment"
    indicators: List[str] = field(default_factory=list)
    spectral_fft_score: float = 0.0
    ela_anomaly_score: float = 0.0
    noise_residual_score: float = 0.0
    metadata_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_ai_generated": self.is_ai_generated,
            "verdict": self.verdict,
            "ai_probability": round(self.ai_probability, 4),
            "authenticity_score": round(self.authenticity_score, 1),
            "confidence_level": self.confidence_level,
            "indicators": self.indicators,
            "spectral_fft_score": round(self.spectral_fft_score, 3),
            "ela_anomaly_score": round(self.ela_anomaly_score, 3),
            "noise_residual_score": round(self.noise_residual_score, 3),
            "metadata_score": round(self.metadata_score, 3)
        }


@dataclass
class PerceptionResult:
    """Result from Layer 2 Perception (YOLOv11 & ResNet-50 & Authenticity)."""
    yolo_objects: List[DetectedObject] = field(default_factory=list)
    yolo_counts: Dict[str, int] = field(default_factory=dict)
    yolo_summary: str = ""
    resnet_top5: List[ImageNetPrediction] = field(default_factory=list)
    resnet_top1: str = ""
    resnet_summary: str = ""
    traffic_violations: List[TrafficViolation] = field(default_factory=list)
    traffic_summary: str = ""
    authenticity: Optional[AuthenticityResult] = None
    annotated_image: Optional[str] = None
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "yolo": {
                "detected_objects": [o.to_dict() for o in self.yolo_objects],
                "object_counts": self.yolo_counts,
                "total_objects": len(self.yolo_objects),
                "summary": self.yolo_summary
            },
            "resnet_imagenet": {
                "top_prediction": self.resnet_top1,
                "top5_predictions": [p.to_dict() for p in self.resnet_top5],
                "summary": self.resnet_summary
            },
            "traffic_analysis": {
                "has_violations": bool(self.traffic_violations),
                "violation_count": len(self.traffic_violations),
                "violations": [v.to_dict() for v in self.traffic_violations],
                "summary": self.traffic_summary
            },
            "authenticity": self.authenticity.to_dict() if self.authenticity else None,
            "annotated_image": self.annotated_image,
            "perception_latency_s": round(self.duration_s, 3)
        }
        return res


@dataclass
class ExtractionResult:
    """Result from Layer 3 Extraction (EasyOCR, PyMuPDF, Office Docs)."""
    raw_text: str = ""
    ocr_spans: List[Dict[str, Any]] = field(default_factory=list)
    mean_ocr_confidence: float = 0.0
    doc_genre: str = "general"
    detected_entities: Dict[str, Any] = field(default_factory=dict)
    table_rows: List[Dict[str, Any]] = field(default_factory=list)
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_genre": self.doc_genre,
            "entities": self.detected_entities,
            "has_table_data": bool(self.table_rows),
            "table_row_count": len(self.table_rows),
            "mean_ocr_confidence": round(self.mean_ocr_confidence, 4),
            "extraction_latency_s": round(self.duration_s, 3)
        }


@dataclass
class ScoringResult:
    """Result from Layer 4 Scoring."""
    realtime_accuracy: float = 95.0       # 0.0 to 100.0%
    overall_confidence: float = 0.95      # 0.00 to 1.00
    visual_confidence: float = 0.0
    textual_confidence: float = 0.0
    grounding_confidence: float = 0.0
    quality_score: float = 1.0
    breakdown: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "realtime_accuracy": round(self.realtime_accuracy, 2),
            "overall_confidence": round(self.overall_confidence, 4),
            "visual_confidence": round(self.visual_confidence, 4),
            "textual_confidence": round(self.textual_confidence, 4),
            "grounding_confidence": round(self.grounding_confidence, 4),
            "quality_score": round(self.quality_score, 3),
            "breakdown": self.breakdown
        }


@dataclass
class ReasoningResult:
    """Result from Layer 5 Reasoning."""
    synthesized_answer: str = ""
    is_hindi: bool = False
    grounded_evidences: List[GroundedEvidence] = field(default_factory=list)
    generator_used: str = "executive_synthesizer"
    duration_s: float = 0.0


@dataclass
class EngineOutput:
    """Master response returned by Layer 7 Orchestration to FastAPI."""
    answer: str
    accuracy: float                       # Real-time percentage e.g. 96.8
    confidence: float                     # Real-time confidence float e.g. 0.968
    pipeline_latency_s: float
    category: str
    dl_metrics: Dict[str, Any]
    grounded_evidences: List[Dict[str, Any]] = field(default_factory=list)
    audio_url: Optional[str] = None
    audio_filename: Optional[str] = None
    annotated_image: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "accuracy": round(self.accuracy, 2),
            "confidence": round(self.confidence, 4),
            "pipeline_latency_s": round(self.pipeline_latency_s, 2),
            "category": self.category,
            "dl_metrics": self.dl_metrics,
            "grounded_evidences": self.grounded_evidences,
            "audio_url": self.audio_url,
            "audio_filename": self.audio_filename,
            "annotated_image": self.annotated_image
        }
