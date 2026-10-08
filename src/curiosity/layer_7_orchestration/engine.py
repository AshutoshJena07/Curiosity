"""Layer 7: Master Orchestration Engine for Curiosity AI.

End-to-End Multimodal Pipeline Coordinating:
- Layer 0: Core Contracts & Config
- Layer 1: Ingestion & PyMuPDF Rasterization
- Layer 2: Perception (YOLOv11 & ResNet-50)
- Layer 3: Extraction (EasyOCR & Document Intelligence)
- Layer 4: Real-time Accuracy & Confidence Scoring
- Layer 5: Grounded Reasoning & Synthesis (Sentence-Transformers)
- Layer 6: Persistence & Cloud Telemetry
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.curiosity.layer_0_core.contracts import (
    EngineOutput,
    ExtractionResult,
    MediaCategory,
    MediaPayload,
    PerceptionResult
)
from src.curiosity.layer_1_ingestion.media_ingestor import MediaIngestor
from src.curiosity.layer_2_perception.vision_pipeline import VisionPerceptionPipeline
from src.curiosity.layer_3_extraction.document_extractor import DocumentIntelligenceExtractor
from src.curiosity.layer_4_scoring.confidence_scorer import RealtimeScorer
from src.curiosity.layer_5_reasoning.grounded_synthesizer import GroundedReasoningEngine
from src.curiosity.layer_6_persistence.persistence_manager import PersistenceManager

logger = logging.getLogger("curiosity.layer_7")


class CuriosityEngine:
    """Master Multimodal Orchestrator coordinating all 7 layers."""

    _session_memory: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def clear_session(cls, session_key: str = "global_workspace_session") -> None:
        cls._session_memory.pop(session_key, None)

    @classmethod
    def execute(
        cls,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        prompt: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        user_name: Optional[str] = None,
        user_id: Optional[str] = None,
        voice: Optional[str] = None,
        emotion: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute end-to-end multimodal pipeline with real-time metrics."""
        t0 = time.time()
        session_key = str(user_id) if user_id else "global_workspace_session"

        # Check for multi-turn session persistence when no new file is passed
        has_cached_media = (not file_bytes) and (session_key in cls._session_memory)

        if has_cached_media:
            cached = cls._session_memory[session_key]
            ingestion = cached["ingestion"]
            perception = cached["perception"]
            extraction = cached["extraction"]
            scoring = cached["scoring"]
            t_ingest = 0.0
        else:
            payload = MediaPayload(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
                user_prompt=prompt,
                history=history or [],
                user_name=user_name,
                user_id=user_id
            )

            # ── STEP 1: LAYER 1 INGESTION & PREPROCESSING ───────────────────
            ingestion = MediaIngestor.ingest(payload)
            t_ingest = time.time() - t0

            # ── STEP 2: LAYER 2 PERCEPTION (YOLOv11 & RESNET-50) ─────────────
            perception = PerceptionResult()
            if ingestion.is_visual or ingestion.image:
                pipeline = VisionPerceptionPipeline.get_instance()
                perception = pipeline.process(ingestion.image)

            # ── STEP 3: LAYER 3 EXTRACTION (EASYOCR & PYMUPDF) ───────────────
            extraction = ExtractionResult()
            if ingestion.category != MediaCategory.TEXT_ONLY:
                extraction = DocumentIntelligenceExtractor.extract(ingestion, payload)

            # ── STEP 4: LAYER 4 REAL-TIME SCORING ────────────────────────────
            scoring = RealtimeScorer.evaluate(
                ingestion=ingestion,
                perception=perception,
                extraction=extraction,
                user_prompt=prompt
            )

            # Cache the active media state for multi-turn follow-up inquiries
            if ingestion.category != MediaCategory.TEXT_ONLY:
                cls._session_memory[session_key] = {
                    "ingestion": ingestion,
                    "perception": perception,
                    "extraction": extraction,
                    "scoring": scoring,
                    "filename": filename,
                    "timestamp": time.time()
                }

        # ── STEP 5: LAYER 5 GROUNDED REASONING & SYNTHESIS ──────────────
        reasoning = GroundedReasoningEngine.synthesize(
            ingestion=ingestion,
            perception=perception,
            extraction=extraction,
            scoring=scoring,
            user_prompt=prompt,
            user_name=user_name,
            history=history or []
        )

        # ── STEP 5B: SCRIPT PERFORMANCE & AUDIO RECORDING ENGINE ───────
        audio_url = None
        audio_filename = None
        from src.curiosity.layer_5_reasoning.script_performer import is_script_performance_request, execute_script_performance
        if is_script_performance_request(prompt):
            doc_context = extraction.raw_text if extraction else ""
            perf_result = execute_script_performance(
                prompt,
                document_text=doc_context,
                user_id=user_id or session_key,
                preferred_voice=voice,
                emotion=emotion
            )
            if perf_result.get("answer"):
                reasoning.synthesized_answer = perf_result.get("answer")
                reasoning.generator_used = "neural_script_performer"
            if perf_result.get("success"):
                audio_url = perf_result.get("audio_url")
                audio_filename = perf_result.get("audio_filename")

        total_latency = time.time() - t0

        # Terminal real-time log
        print(
            f"\n"
            f"===============================================================================\n"
            f"[CuriosityEngine] REAL-TIME INFERENCE TELEMETRY\n"
            f"-------------------------------------------------------------------------------\n"
            f"Media Category : {ingestion.category.value}\n"
            f"Real-time Acc  : {scoring.realtime_accuracy:.2f}%\n"
            f"Confidence     : {scoring.overall_confidence:.4f}\n"
            f"Pipeline Time  : {total_latency:.2f}s (Ingest: {t_ingest:.2f}s | Reasoning: {reasoning.duration_s:.2f}s)\n"
            f"Evidences Found: {len(reasoning.grounded_evidences)} grounded item(s)\n"
            f"Audio Output   : {audio_filename or 'None'}\n"
            f"===============================================================================\n"
        )

        # ── STEP 6: LAYER 6 PERSISTENCE & TELEMETRY ─────────────────────
        PersistenceManager.log_interaction_async(
            user_prompt=prompt,
            assistant_response=reasoning.synthesized_answer,
            media_category=ingestion.category.value,
            accuracy=scoring.realtime_accuracy,
            confidence=scoring.overall_confidence,
            duration_s=total_latency,
            filename=ingestion.filename,
            user_id=user_id,
            extra_metadata=scoring.breakdown
        )

        # Assemble Master DL Metrics dictionary
        dl_metrics = {
            "category": ingestion.category.value,
            "filename": ingestion.filename,
            "perception": perception.to_dict(),
            "extraction": extraction.to_dict(),
            "scoring": scoring.to_dict(),
            "generator": reasoning.generator_used,
            "is_hindi": reasoning.is_hindi
        }

        output = EngineOutput(
            answer=reasoning.synthesized_answer,
            accuracy=scoring.realtime_accuracy,
            confidence=scoring.overall_confidence,
            pipeline_latency_s=round(total_latency, 2),
            category=ingestion.category.value,
            dl_metrics=dl_metrics,
            grounded_evidences=[e.to_dict() for e in reasoning.grounded_evidences],
            audio_url=audio_url,
            audio_filename=audio_filename
        )

        return output.to_dict()
