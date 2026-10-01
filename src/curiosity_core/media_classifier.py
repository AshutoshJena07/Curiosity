"""[FILE 1] Media Classifier & Routing Engine for Curiosity Core.

Analyzes any incoming upload (PDF, Document, Image, Video, Audio, or Text),
validates format integrity, and specifies the exact processing category.
"""

from __future__ import annotations

import io
import mimetypes
import os
from dataclasses import dataclass
from typing import Optional
from PIL import Image

# Core Media Category Constants
CATEGORY_PDF_DOCUMENT = "pdf_document"
CATEGORY_OFFICE_DOCUMENT = "office_document"
CATEGORY_VISUAL_IMAGE = "visual_image"
CATEGORY_VIDEO = "video_media"
CATEGORY_AUDIO = "audio_media"
CATEGORY_TEXT_ONLY = "text_only"

# Extension mappings
DOCUMENT_EXTENSIONS = {
    ".pdf": CATEGORY_PDF_DOCUMENT,
    ".docx": CATEGORY_OFFICE_DOCUMENT,
    ".doc": CATEGORY_OFFICE_DOCUMENT,
    ".xlsx": CATEGORY_OFFICE_DOCUMENT,
    ".xls": CATEGORY_OFFICE_DOCUMENT,
    ".pptx": CATEGORY_OFFICE_DOCUMENT,
    ".ppt": CATEGORY_OFFICE_DOCUMENT,
    ".csv": CATEGORY_OFFICE_DOCUMENT,
    ".txt": CATEGORY_OFFICE_DOCUMENT,
    ".json": CATEGORY_OFFICE_DOCUMENT,
    ".md": CATEGORY_OFFICE_DOCUMENT,
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


@dataclass(frozen=True)
class MediaClassificationResult:
    """Standardized metadata and category routing descriptor."""
    category: str
    filename: str
    extension: str
    mime_type: str
    file_size: int
    is_document: bool
    is_visual: bool
    is_empty: bool
    description: str


class MediaClassifier:
    """File 1 Engine: Inspects, validates, and routes any incoming media input."""

    @classmethod
    def classify(
        cls,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> MediaClassificationResult:
        """Analyze incoming input and return exact media classification."""
        if not file_bytes or len(file_bytes) == 0:
            return MediaClassificationResult(
                category=CATEGORY_TEXT_ONLY,
                filename="none",
                extension="",
                mime_type="text/plain",
                file_size=0,
                is_document=False,
                is_visual=False,
                is_empty=True,
                description="Conversational Text Query (No Media Attached)"
            )

        clean_filename = (filename or "uploaded_media").strip()
        _, ext = os.path.splitext(clean_filename.lower())
        size = len(file_bytes)

        # 1. Resolve MIME type
        resolved_mime = content_type or mimetypes.guess_type(clean_filename)[0] or "application/octet-stream"

        # 2. Check PDF / Office Document by extension or magic header
        if ext == ".pdf" or file_bytes.startswith(b"%PDF-"):
            return MediaClassificationResult(
                category=CATEGORY_PDF_DOCUMENT,
                filename=clean_filename,
                extension=".pdf",
                mime_type="application/pdf",
                file_size=size,
                is_document=True,
                is_visual=False,
                is_empty=False,
                description="PDF Document (Academic Marksheet, Report, Invoice, or Book)"
            )

        if ext in DOCUMENT_EXTENSIONS:
            cat = DOCUMENT_EXTENSIONS[ext]
            return MediaClassificationResult(
                category=cat,
                filename=clean_filename,
                extension=ext,
                mime_type=resolved_mime,
                file_size=size,
                is_document=True,
                is_visual=False,
                is_empty=False,
                description=f"Structured Document / Office File ({ext.upper()})"
            )

        # 3. Check Image by extension or PIL validation
        if ext in IMAGE_EXTENSIONS or resolved_mime.startswith("image/"):
            is_valid_image = False
            try:
                with Image.open(io.BytesIO(file_bytes)) as img:
                    img.verify()
                is_valid_image = True
            except Exception:
                is_valid_image = False

            if is_valid_image or ext in IMAGE_EXTENSIONS:
                return MediaClassificationResult(
                    category=CATEGORY_VISUAL_IMAGE,
                    filename=clean_filename,
                    extension=ext or ".png",
                    mime_type=resolved_mime or "image/png",
                    file_size=size,
                    is_document=False,
                    is_visual=True,
                    is_empty=False,
                    description="Visual Image / Photograph (Scene, Objects, or Scanned Sheet)"
                )

        # 4. Check Video
        if ext in VIDEO_EXTENSIONS or resolved_mime.startswith("video/"):
            return MediaClassificationResult(
                category=CATEGORY_VIDEO,
                filename=clean_filename,
                extension=ext or ".mp4",
                mime_type=resolved_mime or "video/mp4",
                file_size=size,
                is_document=False,
                is_visual=True,
                is_empty=False,
                description="Digital Video Media (Dynamic visual stream)"
            )

        # 5. Check Audio
        if ext in AUDIO_EXTENSIONS or resolved_mime.startswith("audio/"):
            return MediaClassificationResult(
                category=CATEGORY_AUDIO,
                filename=clean_filename,
                extension=ext or ".mp3",
                mime_type=resolved_mime or "audio/mpeg",
                file_size=size,
                is_document=False,
                is_visual=False,
                is_empty=False,
                description="Acoustic Audio Recording"
            )

        # 6. Fallback: try reading as plain text
        try:
            sample = file_bytes[:1024].decode("utf-8")
            return MediaClassificationResult(
                category=CATEGORY_OFFICE_DOCUMENT,
                filename=clean_filename,
                extension=ext or ".txt",
                mime_type="text/plain",
                file_size=size,
                is_document=True,
                is_visual=False,
                is_empty=False,
                description="Plain Text / Data File"
            )
        except UnicodeDecodeError:
            pass

        # Default binary payload
        return MediaClassificationResult(
            category=CATEGORY_VISUAL_IMAGE,
            filename=clean_filename,
            extension=ext or ".bin",
            mime_type=resolved_mime,
            file_size=size,
            is_document=False,
            is_visual=True,
            is_empty=False,
            description="Generic Binary Media"
        )
