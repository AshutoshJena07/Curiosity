"""Universal File Parser for Images, Documents, Spreadsheets, and Text files.

Bridges parsing to Curiosity Core extraction engines and PIL.
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Tuple
from PIL import Image

from src.curiosity_core.content_extractor import ContentExtractor


def parse_uploaded_file(
    file_bytes: bytes,
    filename: str,
    content_type: str = ""
) -> Tuple[Image.Image | None, str]:
    """Process any uploaded file and return a tuple of (pil_image, extracted_text_context).

    - For images: returns (pil_image, "")
    - For documents (PDF, Word, PPT, Excel, Text, Code, CSV, JSON): returns (None, extracted_structured_context)
    """
    ext = Path(filename).suffix.lower()
    content_type = (content_type or "").lower()

    # 1. Image Formats
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif"} or "image/" in content_type:
        try:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            return img, ""
        except Exception:
            pass

    if ext == ".svg":
        svg_text = file_bytes.decode("utf-8", errors="ignore")
        clean_text = re.sub(r"<[^>]+>", " ", svg_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        return None, f"[SVG Vector File Content & Text Elements ({filename})]:\n{clean_text[:2500]}"

    # 2. PDF Documents
    if ext == ".pdf" or "pdf" in content_type:
        pdf_text = ContentExtractor.extract_text_from_pdf(file_bytes)
        return None, pdf_text or f"[PDF Document ({filename})]: Uploaded PDF file contains no readable text."

    # 3. Office Documents, Tabular & Text Files
    office_text = ContentExtractor.extract_text_from_office_doc(file_bytes, filename, content_type)
    return None, office_text
