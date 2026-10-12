"""Layer 2 Visual Annotator: Draws high-precision bounding boxes, labels, and traffic violation overlays."""

from __future__ import annotations

import base64
import io
import logging
import os
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.curiosity.layer_0_core.contracts import DetectedObject, TrafficViolation

logger = logging.getLogger("curiosity.layer_2.annotator")

# Target storage directory for rendered visual outputs
ANNOTATED_DIR = Path(__file__).resolve().parents[3] / "data" / "annotated_images"
ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

# Curated high-contrast color palette (RGB)
CLASS_COLORS = {
    "person": (245, 158, 11),       # Amber
    "motorcycle": (6, 182, 212),     # Cyan
    "bicycle": (14, 165, 233),      # Sky Blue
    "car": (59, 130, 246),          # Blue
    "bus": (99, 102, 241),          # Indigo
    "truck": (139, 92, 246),        # Purple
    "cell phone": (236, 72, 153),   # Pink
    # Wildlife & Animals
    "lion": (234, 88, 12),          # Golden Lion Amber
    "tiger": (249, 115, 22),        # Bright Orange
    "cheetah": (217, 119, 6),       # Cheetah Ochre
    "leopard": (217, 119, 6),       # Leopard Ochre
    "giraffe": (132, 204, 22),      # Lime Green
    "zebra": (71, 85, 105),         # Slate
    "wildebeest": (180, 83, 9),     # Chestnut Brown
    "hartebeest": (180, 83, 9),     # Hartebeest Brown
    "gazelle": (245, 158, 11),      # Amber Gazelle
    "impala": (245, 158, 11),       # Amber Impala
    "antelope": (245, 158, 11),     # Antelope
    "elephant": (100, 116, 139),    # Elephant Slate
    "rhinoceros": (100, 116, 139),  # Rhino Slate
    "hippopotamus": (71, 85, 105),  # Hippo Slate
    "hyena": (161, 98, 7),          # Hyena
    "wolf": (148, 163, 184),        # Wolf Slate
    "fox": (234, 88, 12),           # Fox Orange
    "bear": (120, 53, 15),          # Bear Dark Brown
    "deer": (180, 83, 9),           # Deer Brown
    "dog": (168, 85, 247),          # Purple
    "cat": (236, 72, 153),          # Pink
    "horse": (217, 119, 6),         # Warm Brown
    "sheep": (20, 184, 166),        # Teal
    "cow": (16, 185, 129),          # Emerald
    "bird": (14, 165, 233),         # Sky Blue
}

VIOLATION_RED = (239, 68, 68)       # Red-500
VIOLATION_DARK = (153, 27, 27)      # Red-800
COMPLIANT_GREEN = (34, 197, 94)     # Green-500


class VisualDetectionAnnotator:
    """Overlays YOLO object bounding boxes and traffic violation banners on input images."""

    @classmethod
    def annotate(
        cls,
        image: Image.Image,
        detected_objects: List[DetectedObject],
        traffic_violations: Optional[List[TrafficViolation]] = None,
        task_id: Optional[str] = None
    ) -> Optional[str]:
        """Draws visual detection boxes and violation callouts. Returns relative URL to annotated image."""
        if image is None:
            return None

        try:
            # Clone RGB image to avoid mutating original
            annotated = image.convert("RGB").copy()
            draw = ImageDraw.Draw(annotated)
            w, h = annotated.size

            # Adaptive line thickness and font sizing based on image resolution
            box_width = max(2, int(min(w, h) * 0.004))
            font_size = max(13, int(min(w, h) * 0.024))

            # Attempt to load a clean TTF font; fallback to PIL default
            font = None
            font_candidates = ["arial.ttf", "calibri.ttf", "DejaVuSans.ttf", "seguiemj.ttf"]
            for candidate in font_candidates:
                try:
                    font = ImageFont.truetype(candidate, font_size)
                    break
                except Exception:
                    continue
            if font is None:
                font = ImageFont.load_default()

            # ── 1. DRAW STANDARD OBJECT DETECTION BOUNDING BOXES ────────────
            for obj in detected_objects:
                x1, y1, x2, y2 = obj.box
                # Clamp coordinates to image boundaries
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w - 1, x2), min(h - 1, y2)
                if x2 <= x1 or y2 <= y1:
                    continue

                color = CLASS_COLORS.get(obj.label.lower(), (99, 102, 241))
                # Draw bounding box
                draw.rectangle([x1, y1, x2, y2], outline=color, width=box_width)

                # Format label tag (e.g., 'zebra 0.99' or 'motorcycle 92%')
                conf_pct = f"{obj.confidence:.2f}" if obj.confidence <= 1.0 else f"{obj.confidence:.0f}%"
                label_text = f"{obj.label} {conf_pct}"

                # Calculate text dimensions
                try:
                    tb = draw.textbbox((x1, y1), label_text, font=font)
                    text_w = tb[2] - tb[0]
                    text_h = tb[3] - tb[1]
                except Exception:
                    text_w, text_h = len(label_text) * 8, font_size

                # Position banner above box if space permits; else inside box
                pad = 4
                if y1 >= text_h + pad * 2:
                    pill_y1 = y1 - text_h - pad * 2
                    pill_y2 = y1
                else:
                    pill_y1 = y1
                    pill_y2 = y1 + text_h + pad * 2

                pill_x1 = x1
                pill_x2 = min(w - 1, x1 + text_w + pad * 2)

                # Draw label pill background
                draw.rectangle([pill_x1, pill_y1, pill_x2, pill_y2], fill=color)
                # Draw label text (contrast white or black)
                text_color = (0, 0, 0) if (color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114) > 160 else (255, 255, 255)
                draw.text((pill_x1 + pad, pill_y1 + pad), label_text, fill=text_color, font=font)

            # ── 2. DRAW TRAFFIC RULE VIOLATION CALLOUTS ───────────────────────
            violations = traffic_violations or []
            box_violation_counts = {}

            for v in violations:
                target_box = v.bbox or v.vehicle_bbox
                if not target_box:
                    continue

                vx1, vy1, vx2, vy2 = target_box
                vx1, vy1 = max(0, vx1), max(0, vy1)
                vx2, vy2 = min(w - 1, vx2), min(h - 1, vy2)

                box_key = (round(vx1, 0), round(vy1, 0), round(vx2, 0), round(vy2, 0))
                v_count = box_violation_counts.get(box_key, 0)
                box_violation_counts[box_key] = v_count + 1

                # Draw prominent red warning outline (once per box)
                if v_count == 0:
                    draw.rectangle([vx1, vy1, vx2, vy2], outline=VIOLATION_RED, width=box_width + 1)

                v_label = f"VIOLATION: {v.violation_type.upper()}"
                try:
                    tb = draw.textbbox((vx1, vy1), v_label, font=font)
                    v_w = tb[2] - tb[0]
                    v_h = tb[3] - tb[1]
                except Exception:
                    v_w, v_h = len(v_label) * 8, font_size

                v_pad = 5
                # Vertically offset each violation pill so multiple rules are stacked and readable
                offset_y = v_count * (v_h + v_pad * 2 + 3)
                v_pill_y1 = min(h - v_h - v_pad * 2, max(0, vy1 + offset_y))
                v_pill_y2 = min(h - 1, v_pill_y1 + v_h + v_pad * 2)
                v_pill_x1 = vx1
                v_pill_x2 = min(w - 1, vx1 + v_w + v_pad * 2)

                draw.rectangle([v_pill_x1, v_pill_y1, v_pill_x2, v_pill_y2], fill=VIOLATION_RED)
                draw.text((v_pill_x1 + v_pad, v_pill_y1 + v_pad), v_label, fill=(255, 255, 255), font=font)

            # ── 3. SAVE TO DISK & RETURN SERVE URL ────────────────────────────
            file_id = task_id or f"annotated_{uuid.uuid4().hex[:12]}"
            filename = f"{file_id}.jpg"
            save_path = ANNOTATED_DIR / filename

            annotated.save(save_path, format="JPEG", quality=90)
            logger.info(f"[VisualAnnotator] Saved annotated detection overlay to {save_path}")

            # Return the standard API URL
            return f"/api/v1/annotated/{filename}"

        except Exception as exc:
            logger.error(f"[VisualAnnotator] Failed to render visual overlay: {exc}")
            return None
