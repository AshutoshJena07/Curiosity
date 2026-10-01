"""[FILE 2] Content Extractor & JSON Structurer Engine for Curiosity Core.

Analyzes the media input routed by File 1:
- If PDF/Document: extracts multi-page text, table rows, key-values, and detects language.
- If Visual Image: executes YOLOv8 object detection, ResNet-50 classification, and scene analysis.
- If Office File: extracts tabular/textual context.
Converts all raw intelligence into a standardized, rich JSON schema.
"""

from __future__ import annotations

import io
import json
import os
import re
from typing import Any, Dict, List, Optional
from PIL import Image

from src.curiosity_core.media_classifier import (
    CATEGORY_PDF_DOCUMENT,
    CATEGORY_OFFICE_DOCUMENT,
    CATEGORY_VISUAL_IMAGE,
    CATEGORY_VIDEO,
    CATEGORY_AUDIO,
    CATEGORY_TEXT_ONLY,
    MediaClassificationResult
)

# ── 1. Pure Python Language & Document Pattern Detector ───────────────────────

class DocumentPatternDetector:
    """Detects language, script, document genre, and key entities dynamically."""

    @classmethod
    def detect_language(cls, text: str) -> Dict[str, Any]:
        """Detect language using Unicode ranges and character distributions."""
        if not text or not text.strip():
            return {"language": "Unknown", "script": "None", "confidence": 0.0}

        scripts = {
            "Devanagari (Hindi/Marathi)": len(re.findall(r'[\u0900-\u097F]', text)),
            "Bengali": len(re.findall(r'[\u0980-\u09FF]', text)),
            "Odia": len(re.findall(r'[\u0B00-\u0B7F]', text)),
            "Tamil": len(re.findall(r'[\u0B80-\u0BFF]', text)),
            "Telugu": len(re.findall(r'[\u0C00-\u0C7F]', text)),
            "Arabic / Urdu": len(re.findall(r'[\u0600-\u06FF]', text)),
            "Chinese / Japanese": len(re.findall(r'[\u4E00-\u9FFF]', text)),
            "Latin / English": len(re.findall(r'[a-zA-Z]', text)),
        }

        total_letters = sum(scripts.values())
        if total_letters == 0:
            return {"language": "Undetermined", "script": "Symbols/Numbers", "confidence": 0.0}

        top_script, count = max(scripts.items(), key=lambda item: item[1])
        confidence_pct = round((count / total_letters) * 100, 1)

        if "Latin" in top_script:
            lang_name = "English"
        elif "Devanagari" in top_script:
            lang_name = "Hindi"
        elif "Odia" in top_script:
            lang_name = "Odia"
        elif "Bengali" in top_script:
            lang_name = "Bengali"
        else:
            lang_name = top_script.split()[0]

        return {
            "language": lang_name,
            "script": top_script,
            "confidence": confidence_pct
        }

    @classmethod
    def classify_document_genre(cls, text: str) -> str:
        """Classify document genre from semantic keywords."""
        lower = text.lower()
        scores = {
            "Academic Marksheet / Transcript": sum(1 for w in ["marks", "grade", "transcript", "semester", "cgpa", "sgpa", "roll no", "registration", "passed", "subject", "examination", "course", "credits", "secured", "bse", "board"] if w in lower),
            "Certificate / Award / Diploma": sum(1 for w in ["certificate", "certified", "conferred", "awarded", "diploma", "degree", "hereby certifies", "achievement", "completed", "appreciation"] if w in lower),
            "Billing Invoice / Financial Receipt": sum(1 for w in ["invoice", "tax invoice", "bill to", "ship to", "gstin", "subtotal", "total amount", "due date", "amount due", "payment", "unit price", "receipt"] if w in lower),
            "Medical Report / Clinical Summary": sum(1 for w in ["patient", "doctor", "diagnosis", "hospital", "clinic", "prescription", "rx", "symptoms", "dosage", "clinical", "pathology", "lab report"] if w in lower),
            "Identity Document / Official Card": sum(1 for w in ["identity card", "id no", "dob", "date of birth", "valid till", "blood group", "gender", "father's name", "aadhaar", "passport", "driving licence"] if w in lower),
            "Legal Agreement / Contract": sum(1 for w in ["agreement", "contract", "parties", "witnesseth", "whereas", "terms and conditions", "clause", "jurisdiction", "arbitration"] if w in lower),
            "Professional Resume / CV": sum(1 for w in ["resume", "curriculum vitae", "education", "experience", "skills", "projects", "work history", "summary", "employment"] if w in lower),
        }

        top_type, top_score = max(scores.items(), key=lambda item: item[1])
        return top_type if top_score >= 2 else "General Document"

    @classmethod
    def extract_document_entities(cls, text: str) -> Dict[str, Any]:
        """Extract header, key-value pairs, dates, IDs, and financial figures."""
        lines = [l.strip() for l in text.replace("\r", " ").splitlines() if l.strip()]

        # 1. Organization / Header
        headers = []
        for line in lines[:8]:
            if len(line) >= 4 and not re.match(r'^[0-9\W]+$', line) and not line.startswith("[") and not line.startswith("•"):
                if not any(line.lower().startswith(p) for p in ["document", "primary language", "detected", "raw extracted"]):
                    headers.append(line)
        main_header = headers[0] if headers else None

        # 2. Key-Value Pairs
        kv_pairs = {}
        for line in lines:
            if line.startswith("[") or line.startswith("•"):
                continue
            m = re.match(r"^([A-Za-z0-9\s/'\.\(\)\-_]{3,45})[:\-=]\s*(.{1,120})$", line)
            if m:
                k = m.group(1).strip().title()
                v = m.group(2).strip()
                if k not in kv_pairs and len(v) >= 1 and not v.startswith("["):
                    kv_pairs[k] = v

        # 3. Dates
        dates = re.findall(
            r'\b(?:\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}|\b(?:Summer|Winter|Spring|Fall|Autumn)[-\s]+\d{4})\b',
            text,
            re.I
        )

        # 4. Identification numbers (must have at least one digit)
        id_numbers = re.findall(
            r'\b(?:No|ID|Reg|Ref|Roll|Code|Num|Invoice|Bill|Case)[.:\s#]*([A-Z0-9\-_]{4,22})\b',
            text,
            re.I
        )
        filtered_ids = [
            i for i in id_numbers
            if any(c.isdigit() for c in i) and i.upper() not in {"ULAR", "NONE", "NULL", "TRUE", "FALSE", "CODE", "DATE", "CARD", "BERS"}
        ]

        # 5. Financial figures
        amounts = re.findall(r'(?:[\$€£₹]|Rs\.?|USD|INR)\s*[\d,]+(?:\.\d{2})?', text)

        # 6. Structured Table / Subject Lines Detection
        table_rows = []

        # Strategy A: University Grade Cards (Code, Subject Name, Type, Credits, Letter Grade)
        grade_pattern = re.compile(
            r'^\s*(?:\d{1,2}\s+)?([A-Z]{2,6}\d{2,5})\s+([A-Za-z0-9\s&/\-_]{4,55}?)\s+(Theory\+Practice|Theory\+Project|Project|TPP|Theory|Practice|Lab|Practical)?\s*(\d{1,2}(?:\.\d{1,2})?)\s+([A-FOa-fo][\+\-]?)\s*$',
            re.I | re.M
        )
        for match in grade_pattern.finditer(text):
            code = (match.group(1) or "").strip().upper()
            name = match.group(2).strip().title()
            stype = (match.group(3) or "").strip()
            credits_val = match.group(4).strip()
            grade_val = match.group(5).strip().upper()
            status = "Backlog / Fail" if grade_val in {"F", "FAIL"} else "Pass"
            table_rows.append({
                "code": code,
                "item_or_subject": name,
                "type": stype or "General",
                "full_value": credits_val,
                "secured_value": grade_val,
                "status": status
            })

        # Strategy B: Traditional Marksheets (Code, Subject Name, Full Marks, Secured Marks)
        if not table_rows:
            subject_pattern = re.compile(r'^\s*(?:\d{1,2}\s+)?([A-Z]{2,5}\d{2,4})?\s+([A-Za-z\s&]{4,40})\s+(\d{1,3})\s+(\d{1,3})\s*$', re.M)
            for match in subject_pattern.finditer(text):
                code = (match.group(1) or "").strip()
                name = match.group(2).strip()
                full_m = match.group(3).strip()
                sec_m = match.group(4).strip()
                if name.lower() not in {"total", "full marks", "subject name"}:
                    status = "Pass" if int(sec_m) >= 30 else "Backlog / Fail"
                    table_rows.append({
                        "code": code or "-",
                        "item_or_subject": name,
                        "type": "Theory",
                        "full_value": full_m,
                        "secured_value": sec_m,
                        "status": status
                    })

        return {
            "header": main_header,
            "key_values": kv_pairs,
            "dates": list(set(dates))[:5],
            "reference_ids": list(set(filtered_ids))[:5],
            "financial_amounts": list(set(amounts))[:5],
            "detected_table_rows": table_rows[:25]
        }


# ── 2. Content Extractor Core ─────────────────────────────────────────────────

class ContentExtractor:
    """File 2 Engine: Extracts raw text or visual intelligence, returning a clean JSON schema."""

    _ocr_reader = None

    @classmethod
    def _get_ocr_reader(cls):
        """Lazy loader for EasyOCR."""
        if cls._ocr_reader is None:
            try:
                import easyocr
                import torch
                cls._ocr_reader = easyocr.Reader(["en"], gpu=torch.cuda.is_available(), verbose=False)
            except Exception as exc:
                print(f"[ContentExtractor OCR Warning] EasyOCR could not be initialized: {exc}")
                return None
        return cls._ocr_reader

    @classmethod
    def extract_text_from_pdf(cls, file_bytes: bytes) -> str:
        """Extract multi-page text from digital or scanned PDF."""
        extracted_pages = []
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and len(text.strip()) > 30:
                    extracted_pages.append(f"--- Page {i+1} ---\n{text.strip()}")
        except Exception:
            pass

        # If digital extraction yielded sufficient text, return it
        if extracted_pages:
            return "\n\n".join(extracted_pages)

        # Scanned PDF Fallback: Render first 3 pages as images and run EasyOCR
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            ocr_reader = cls._get_ocr_reader()
            if ocr_reader:
                for i in range(min(len(doc), 3)):
                    page = doc[i]
                    pix = page.get_pixmap(dpi=150)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    import numpy as np
                    results = ocr_reader.readtext(np.array(img), detail=0, paragraph=True)
                    if results:
                        extracted_pages.append(f"--- Scanned Page {i+1} ---\n" + "\n".join(results))
        except Exception:
            pass

        return "\n\n".join(extracted_pages) if extracted_pages else ""

    @classmethod
    def extract_text_from_image(cls, image: Image.Image) -> str:
        """Run OCR on image to extract textual contents."""
        ocr_reader = cls._get_ocr_reader()
        if not ocr_reader:
            return ""
        try:
            import numpy as np
            w, h = image.size
            ocr_img = image.convert("RGB")
            if max(w, h) > 2000:
                ocr_img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
            elif max(w, h) < 600:
                ocr_img = ocr_img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
            results = ocr_reader.readtext(np.array(ocr_img), detail=0, paragraph=True)
            return "\n".join(results).strip()
        except Exception as exc:
            print(f"[ContentExtractor OCR Error] {exc}")
            return ""

    @classmethod
    def extract_visual_deep_learning(cls, image: Image.Image) -> Dict[str, Any]:
        """Execute YOLOv8 Object Detection and ResNet-50 ImageNet Classification."""
        visual_data = {
            "yolo_detections": [],
            "yolo_summary": "",
            "resnet_top5": [],
            "resnet_top1": "",
            "observations": []
        }

        try:
            from src.curiosity_core.deep_learning_pipeline import get_dl_pipeline
            dl_result = get_dl_pipeline().analyze(image)
            if dl_result:
                visual_data["yolo_detections"] = [obj.to_dict() for obj in dl_result.yolo_objects]
                visual_data["yolo_summary"] = dl_result.yolo_summary
                visual_data["resnet_top5"] = [pred.to_dict() for pred in dl_result.resnet_top5]
                visual_data["resnet_top1"] = dl_result.resnet_top1_label
                if dl_result.yolo_summary:
                    visual_data["observations"].append(dl_result.yolo_summary)
                if dl_result.resnet_top1_label:
                    visual_data["observations"].append(f"ImageNet Category: {dl_result.resnet_top1_label}")
        except Exception as exc:
            print(f"[ContentExtractor DeepLearning Notice] DL pipeline skipped: {exc}")

        return visual_data

    @classmethod
    def extract_text_from_office_doc(
        cls,
        file_bytes: bytes,
        filename: str,
        mime_type: str = ""
    ) -> str:
        """Extract structured text from Word, Excel, PowerPoint, CSV, JSON, and text files."""
        if not file_bytes:
            return ""

        _, ext = os.path.splitext(filename.lower())

        # 1. Word Documents (.docx, .doc)
        if ext in {".docx", ".doc"}:
            try:
                import docx
                doc = docx.Document(io.BytesIO(file_bytes))
                paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                tables_text = []
                for t in doc.tables:
                    for row in t.rows:
                        row_line = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_line:
                            tables_text.append(row_line)
                full_doc = "\n".join(paragraphs)
                if tables_text:
                    full_doc += "\n\n[Structured Tables in Document]:\n" + "\n".join(tables_text[:40])
                return f"[Word Document Content ({filename}) - {len(paragraphs)} Paragraphs, {len(doc.tables)} Tables]:\n{full_doc[:4500]}"
            except Exception as e:
                return f"[Word Document Error]: Could not read docx ({e})."

        # 2. Excel Spreadsheets (.xlsx, .xls)
        if ext in {".xlsx", ".xls"}:
            try:
                import pandas as pd
                excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
                sheet_summaries = []
                for sheet in excel_file.sheet_names[:4]:
                    df_sheet = pd.read_excel(excel_file, sheet_name=sheet)
                    rows, cols = df_sheet.shape
                    sheet_summaries.append(
                        f"Sheet '{sheet}': {rows} rows x {cols} columns (Columns: {list(df_sheet.columns)[:8]})\n"
                        f"Sample:\n{df_sheet.head(6).to_string(index=False)}"
                    )
                summary_text = "\n\n".join(sheet_summaries)
                return f"[Excel Workbook Intelligence ({filename}) - {len(excel_file.sheet_names)} Sheets]:\n{summary_text[:4000]}"
            except Exception as e:
                return f"[Excel Read Notice]: {e}"

        # 3. PowerPoint Presentations (.pptx, .ppt)
        if ext in {".pptx", ".ppt"}:
            try:
                import pptx
                prs = pptx.Presentation(io.BytesIO(file_bytes))
                slide_texts = []
                for i, slide in enumerate(prs.slides):
                    st = []
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text.strip():
                            st.append(shape.text.strip())
                    if st:
                        slide_texts.append(f"--- Slide {i+1} ---\n" + "\n".join(st))
                full_ppt = "\n\n".join(slide_texts)
                return f"[PowerPoint Presentation Content ({filename}) - {len(prs.slides)} Slides]:\n{full_ppt[:4500]}"
            except Exception as e:
                return f"[PowerPoint Error]: Could not read pptx ({e})."

        # 4. CSV Files (.csv)
        if ext == ".csv":
            try:
                import pandas as pd
                df = pd.read_csv(io.BytesIO(file_bytes))
                rows, cols = df.shape
                col_names = [str(c) for c in df.columns]
                sample_str = df.head(8).to_string(index=False)
                return (
                    f"[Structured CSV Intelligence: '{filename}']\n"
                    f"Size: {rows} records x {cols} columns\n"
                    f"Columns: {', '.join(col_names[:10])}\n\n"
                    f"Sample Rows:\n{sample_str}"
                )
            except Exception:
                text = file_bytes.decode("utf-8", errors="ignore")
                return f"[CSV Data Table ({filename})]:\n{text[:3000]}"

        # 5. JSON Files (.json)
        if ext == ".json":
            try:
                data = json.loads(file_bytes.decode("utf-8", errors="ignore"))
                if isinstance(data, list):
                    sample = json.dumps(data[:3], indent=2)
                    return f"[Structured JSON Array Intelligence: '{filename}']\nCollection of {len(data)} items.\nSample:\n{sample}"
                elif isinstance(data, dict):
                    sample = json.dumps({k: data[k] for k in list(data.keys())[:10]}, indent=2)
                    return f"[Structured JSON Object Intelligence: '{filename}']\nKeys: {list(data.keys())[:10]}\nSample:\n{sample}"
                else:
                    return f"[Structured JSON Intelligence: '{filename}']:\n{json.dumps(data, indent=2)[:3000]}"
            except Exception:
                text = file_bytes.decode("utf-8", errors="ignore")
                return f"[JSON Data ({filename})]:\n{text[:3000]}"

        # 6. Plain text, markdown, code, and generic text files
        try:
            raw_text = file_bytes.decode("utf-8", errors="ignore").strip()
            if raw_text:
                return f"[Text/Code File Content ({filename}) - Size: {len(raw_text)} chars]:\n{raw_text[:4500]}"
        except Exception:
            pass

        return f"[Uploaded File Metadata]: Filename '{filename}', size {len(file_bytes)} bytes."

    @classmethod
    def process_to_json(
        cls,
        classification: MediaClassificationResult,
        file_bytes: Optional[bytes] = None,
        user_prompt: str = ""
    ) -> Dict[str, Any]:
        """Convert any media input into our standardized ExtractionData JSON schema."""
        cat = classification.category
        extracted_text = ""
        visual_intel = {}
        doc_intel = {}
        language_info = {"language": "English", "script": "Latin / English", "confidence": 100.0}

        # ── PATH A: PDF & Multi-page Documents ──
        if cat == CATEGORY_PDF_DOCUMENT and file_bytes:
            extracted_text = cls.extract_text_from_pdf(file_bytes)
            if extracted_text:
                language_info = DocumentPatternDetector.detect_language(extracted_text)
                genre = DocumentPatternDetector.classify_document_genre(extracted_text)
                entities = DocumentPatternDetector.extract_document_entities(extracted_text)
                doc_intel = {
                    "genre": genre,
                    **entities
                }

        # ── PATH B: Office Documents (Word, Excel, TXT, CSV) ──
        elif cat == CATEGORY_OFFICE_DOCUMENT and file_bytes:
            extracted_text = cls.extract_text_from_office_doc(
                file_bytes, classification.filename, classification.mime_type
            )

            if extracted_text:
                language_info = DocumentPatternDetector.detect_language(extracted_text)
                genre = DocumentPatternDetector.classify_document_genre(extracted_text)
                entities = DocumentPatternDetector.extract_document_entities(extracted_text)
                doc_intel = {"genre": genre, **entities}

        # ── PATH C: Visual Images & Photos ──
        elif cat == CATEGORY_VISUAL_IMAGE and file_bytes:
            try:
                pil_image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            except Exception:
                pil_image = None

            if pil_image:
                # 1. Check if image has document-like text
                extracted_text = cls.extract_text_from_image(pil_image)

                # 2. Run Deep Learning Object Detection & Classification
                visual_intel = cls.extract_visual_deep_learning(pil_image)

                if extracted_text and len(extracted_text.strip()) > 30:
                    language_info = DocumentPatternDetector.detect_language(extracted_text)
                    genre = DocumentPatternDetector.classify_document_genre(extracted_text)
                    entities = DocumentPatternDetector.extract_document_entities(extracted_text)
                    doc_intel = {"genre": genre, **entities}

        # Assemble Master JSON Schema
        master_json = {
            "media_category": cat,
            "filename": classification.filename,
            "file_size": classification.file_size,
            "user_prompt": user_prompt,
            "language": language_info,
            "document_intelligence": doc_intel,
            "visual_intelligence": visual_intel,
            "raw_text": extracted_text[:5000],
            "has_table_data": bool(doc_intel.get("detected_table_rows")),
            "status": "extracted_success"
        }

        return master_json
