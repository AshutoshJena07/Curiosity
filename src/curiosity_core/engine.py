"""Master Curiosity Logic Engine.

Unifies:
1. MediaClassifier (File 1)
2. ContentExtractor (File 2)
3. ExecutiveSynthesizer (File 3)
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from src.curiosity_core.media_classifier import MediaClassifier
from src.curiosity_core.content_extractor import ContentExtractor
from src.curiosity_core.executive_synthesizer import ExecutiveSynthesizer


class CuriosityEngine:
    """End-to-End Scratch Pipeline coordinating Media Classification, Extraction, and Synthesis."""

    @classmethod
    def execute(
        cls,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        prompt: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        user_name: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute the entire 3-file scratch pipeline within < 20 seconds."""
        t0 = time.time()

        # Step 1: Media Classifier & Router
        classification = MediaClassifier.classify(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type
        )
        print(f"[CuriosityEngine] Step 1 Classified: {classification.category} ({classification.description})")

        # Step 2: Content Extractor & JSON Structurer
        extraction_json = ContentExtractor.process_to_json(
            classification=classification,
            file_bytes=file_bytes,
            user_prompt=prompt
        )
        print(f"[CuriosityEngine] Step 2 Extracted JSON: {extraction_json.get('media_category')} (Table data: {extraction_json.get('has_table_data')})")

        # Step 3: Executive Compressor & Frontend Synthesizer
        result = ExecutiveSynthesizer.synthesize(
            extraction_json=extraction_json,
            user_prompt=prompt,
            history=history,
            user_name=user_name,
            user_id=user_id
        )

        total_time = time.time() - t0
        print(f"[CuriosityEngine] Step 3 Pipeline Complete in {total_time:.2f}s (Target: < 20s)")
        result["pipeline_latency_s"] = round(total_time, 2)
        return result
