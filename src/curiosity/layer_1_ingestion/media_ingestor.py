"""Layer 1: Ingestion & Validation Module for Curiosity AI.

Responsible for:
- Format integrity inspection (Magic numbers, MIME types, extensions)
- PDF Ingestion and rasterization via PyMuPDF (fitz)
- Image enhancement (CLAHE, Laplacian variance quality assessment)
- Office document & text validation
"""

from __future__ import annotations

import io
import mimetypes
import os
from typing import Any, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image
import pymupdf  # Official modern PyMuPDF

from src.curiosity.layer_0_core.contracts import (
    IngestionResult,
    MediaCategory,
    MediaPayload
)

DOCUMENT_EXTENSIONS = {
    ".pdf": MediaCategory.PDF_DOCUMENT,
    ".docx": MediaCategory.OFFICE_DOCUMENT,
    ".doc": MediaCategory.OFFICE_DOCUMENT,
    ".xlsx": MediaCategory.OFFICE_DOCUMENT,
    ".xls": MediaCategory.OFFICE_DOCUMENT,
    ".pptx": MediaCategory.OFFICE_DOCUMENT,
    ".ppt": MediaCategory.OFFICE_DOCUMENT,
    ".csv": MediaCategory.OFFICE_DOCUMENT,
    ".txt": MediaCategory.OFFICE_DOCUMENT,
    ".json": MediaCategory.OFFICE_DOCUMENT,
    ".md": MediaCategory.OFFICE_DOCUMENT,
}

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif"
}

VIDEO_EXTENSIONS = {
    ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"
}

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"
}


class MediaIngestor:
    """Ingests, validates, preprocesses, and rasterizes any incoming media stream."""

    @classmethod
    def calculate_laplacian_sharpness(cls, cv2_img: np.ndarray) -> float:
        """Calculate variance of the Laplacian as a metric of image sharpness."""
        try:
            if len(cv2_img.shape) == 3:
                gray = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = cv2_img
            lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            # Normalize to 0.0 - 1.0 (lap_var > 300 is usually very sharp)
            normalized = min(1.0, max(0.05, lap_var / 300.0))
            return normalized
        except Exception:
            return 0.85

    @classmethod
    def apply_adaptive_preprocessing(cls, pil_img: Image.Image) -> Tuple[Image.Image, float]:
        """Apply CLAHE and dynamic contrast enhancement if image is underexposed."""
        try:
            rgb_arr = np.array(pil_img.convert("RGB"))
            bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            quality_score = cls.calculate_laplacian_sharpness(bgr_arr)

            # Check mean brightness
            gray = cv2.cvtColor(bgr_arr, cv2.COLOR_BGR2GRAY)
            mean_brightness = float(np.mean(gray))

            # Apply CLAHE if underexposed (< 85) or overexposed (> 210)
            if mean_brightness < 85 or mean_brightness > 210:
                lab = cv2.cvtColor(bgr_arr, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                cl = clahe.apply(l)
                enhanced_lab = cv2.merge((cl, a, b))
                enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
                enhanced_rgb = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2RGB)
                return Image.fromarray(enhanced_rgb), quality_score

            return pil_img, quality_score
        except Exception:
            return pil_img, 0.90

    @classmethod
    def rasterize_pdf_pages(cls, pdf_bytes: bytes, max_pages: int = 3) -> Tuple[int, List[Image.Image]]:
        """Extract page count and rasterize top pages into high-res PIL images using PyMuPDF."""
        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(doc)
            images: List[Image.Image] = []

            # 2.0 zoom factor gives crisp 144 DPI ideal for OCR
            zoom = 2.0
            mat = pymupdf.Matrix(zoom, zoom)

            for page_idx in range(min(page_count, max_pages)):
                page = doc[page_idx]
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)

            doc.close()
            return page_count, images
        except Exception as exc:
            print(f"[MediaIngestor] PyMuPDF rasterization notice: {exc}")
            return 0, []

    @classmethod
    def ingest(cls, payload: MediaPayload) -> IngestionResult:
        """Analyze incoming input payload and generate standardized IngestionResult."""
        file_bytes = payload.file_bytes
        if not file_bytes or len(file_bytes) == 0:
            return IngestionResult(
                category=MediaCategory.TEXT_ONLY,
                filename="none",
                extension="",
                mime_type="text/plain",
                file_size=0,
                is_document=False,
                is_visual=False,
                is_empty=True,
                description="Conversational Text Query",
                quality_score=1.0
            )

        clean_filename = (payload.filename or "uploaded_file").strip()
        _, ext = os.path.splitext(clean_filename.lower())
        size = len(file_bytes)
        resolved_mime = payload.content_type or mimetypes.guess_type(clean_filename)[0] or "application/octet-stream"

        # 1. PDF Documents
        if ext == ".pdf" or file_bytes.startswith(b"%PDF-"):
            page_count, raster_images = cls.rasterize_pdf_pages(file_bytes, max_pages=3)
            return IngestionResult(
                category=MediaCategory.PDF_DOCUMENT,
                filename=clean_filename,
                extension=".pdf",
                mime_type="application/pdf",
                file_size=size,
                is_document=True,
                is_visual=False,
                is_empty=False,
                description=f"PDF Document ({page_count} Pages)",
                image=raster_images[0] if raster_images else None,
                pdf_page_count=page_count,
                pdf_raster_images=raster_images,
                quality_score=0.98
            )

        # 2. Office Documents
        if ext in DOCUMENT_EXTENSIONS:
            return IngestionResult(
                category=DOCUMENT_EXTENSIONS[ext],
                filename=clean_filename,
                extension=ext,
                mime_type=resolved_mime,
                file_size=size,
                is_document=True,
                is_visual=False,
                is_empty=False,
                description=f"Document ({ext.upper()})",
                quality_score=1.0
            )

        # 3. Visual Images
        if ext in IMAGE_EXTENSIONS or resolved_mime.startswith("image/"):
            try:
                pil_img = Image.open(io.BytesIO(file_bytes))
                pil_img.load()
                processed_img, quality = cls.apply_adaptive_preprocessing(pil_img)
                return IngestionResult(
                    category=MediaCategory.VISUAL_IMAGE,
                    filename=clean_filename,
                    extension=ext or ".png",
                    mime_type=resolved_mime or "image/png",
                    file_size=size,
                    is_document=False,
                    is_visual=True,
                    is_empty=False,
                    description=f"Visual Image ({processed_img.width}x{processed_img.height})",
                    image=processed_img,
                    quality_score=quality
                )
            except Exception as exc:
                print(f"[MediaIngestor] Image loading error: {exc}")

        # 4. Videos
        if ext in VIDEO_EXTENSIONS or resolved_mime.startswith("video/"):
            return IngestionResult(
                category=MediaCategory.VIDEO,
                filename=clean_filename,
                extension=ext or ".mp4",
                mime_type=resolved_mime or "video/mp4",
                file_size=size,
                is_document=False,
                is_visual=True,
                is_empty=False,
                description="Video Media Stream",
                quality_score=0.90
            )

        # 5. Audio
        if ext in AUDIO_EXTENSIONS or resolved_mime.startswith("audio/"):
            return IngestionResult(
                category=MediaCategory.AUDIO,
                filename=clean_filename,
                extension=ext or ".mp3",
                mime_type=resolved_mime or "audio/mpeg",
                file_size=size,
                is_document=False,
                is_visual=False,
                is_empty=False,
                description="Audio Acoustic Recording",
                quality_score=0.90
            )

        # 6. Fallback: Check if valid UTF-8 text
        try:
            sample = file_bytes[:1024].decode("utf-8")
            return IngestionResult(
                category=MediaCategory.OFFICE_DOCUMENT,
                filename=clean_filename,
                extension=ext or ".txt",
                mime_type="text/plain",
                file_size=size,
                is_document=True,
                is_visual=False,
                is_empty=False,
                description="Plain Text Document",
                quality_score=1.0
            )
        except UnicodeDecodeError:
            pass

        return IngestionResult(
            category=MediaCategory.VISUAL_IMAGE,
            filename=clean_filename,
            extension=ext or ".bin",
            mime_type=resolved_mime,
            file_size=size,
            is_document=False,
            is_visual=True,
            is_empty=False,
            description="Generic Binary Media",
            quality_score=0.85
        )
