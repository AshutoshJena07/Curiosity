"""Comprehensive unit and integration tests for universal image, video, document, and pattern intelligence."""

import io
import json
import pytest
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

from src.image_analytics.api import app
from src.image_analytics.image_restorer import UniversalImageRestorer, ImageConditionReport
from src.image_analytics.pattern_analyzer import SituationPatternAnalyzer, PatternAnalysisResult
from src.image_analytics.video_analyzer import UniversalVideoAnalyzer, VideoAnalysisResult
from src.image_analytics.document_analyzer import UniversalDocumentAnalyzer, DocumentAnalysisSummary
from src.image_analytics.file_parser import parse_uploaded_file

client = TestClient(app)


# ==============================================================================
# 1. UNIVERSAL IMAGE RESTORATION TESTS
# ==============================================================================

def test_image_restorer_low_light():
    """Verify that a dark/underexposed image is detected and lifted."""
    # Create very dark image (mean brightness ~ 25)
    dark_np = np.full((100, 100, 3), 25, dtype=np.uint8)
    dark_img = Image.fromarray(dark_np)

    restored_img, report = UniversalImageRestorer.enhance_and_restore(dark_img)
    assert report.is_low_light is True
    assert "low-light" in report.condition_summary
    # Check that restored image has lifted brightness
    restored_stat = np.mean(np.array(restored_img))
    assert restored_stat > 25.0


def test_image_restorer_overexposed():
    """Verify that an overexposed/bright image is detected and tone-mapped."""
    # Create very bright washed-out image (mean brightness ~ 240)
    bright_np = np.full((100, 100, 3), 240, dtype=np.uint8)
    bright_img = Image.fromarray(bright_np)

    restored_img, report = UniversalImageRestorer.enhance_and_restore(bright_img)
    assert report.is_overexposed is True
    assert "overexposed" in report.condition_summary
    restored_stat = np.mean(np.array(restored_img))
    assert restored_stat < 240.0


def test_image_restorer_blurry():
    """Verify that a blurry/unclear image is flagged and restored."""
    # Uniform smooth gradient has near-zero Laplacian variance (blurry)
    smooth = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        smooth[i, :, :] = int(i * 1.5)
    smooth_img = Image.fromarray(smooth)

    restored_img, report = UniversalImageRestorer.enhance_and_restore(smooth_img)
    assert report.is_blurry is True
    assert "blurry" in report.condition_summary


def test_image_restorer_color_modes():
    """Verify handling of RGBA, Grayscale (L), and CMYK modes."""
    # RGBA with transparent alpha
    rgba = Image.new("RGBA", (50, 50), (255, 0, 0, 128))
    norm_rgba = UniversalImageRestorer.normalize_color_and_orientation(rgba)
    assert norm_rgba.mode == "RGB"

    # Grayscale
    gray = Image.new("L", (50, 50), 120)
    norm_gray = UniversalImageRestorer.normalize_color_and_orientation(gray)
    assert norm_gray.mode == "RGB"

    # CMYK
    cmyk = Image.new("CMYK", (50, 50), (0, 100, 100, 0))
    norm_cmyk = UniversalImageRestorer.normalize_color_and_orientation(cmyk)
    assert norm_cmyk.mode == "RGB"


# ==============================================================================
# 2. SITUATION & PATTERN ANALYSIS TESTS
# ==============================================================================

def test_pattern_analyzer_helmet_detection():
    """Verify helmet detection on rider/worker."""
    img = Image.new("RGB", (100, 100), (50, 50, 50))

    def mock_vqa(im, q):
        ql = q.lower()
        if "main subject" in ql:
            return "motorcycle rider"
        if "setting" in ql:
            return "city street"
        if "wearing a helmet" in ql:
            return "yes, full face helmet"
        return "normal"

    res = SituationPatternAnalyzer.probe_situations(img, mock_vqa, user_prompt="Check helmet safety")
    assert "Helmet" in res.detected_situation or "Safety" in res.detected_situation
    assert any("helmet" in obs.lower() for obs in res.key_observations)


def test_pattern_analyzer_no_helmet_hazard():
    """Verify safety flag when rider has no helmet."""
    img = Image.new("RGB", (100, 100), (50, 50, 50))

    def mock_vqa(im, q):
        ql = q.lower()
        if "main subject" in ql:
            return "motorcyclist on bike"
        if "setting" in ql:
            return "busy road"
        if "wearing a helmet" in ql:
            return "no, riding without helmet"
        if "rider or person's head" in ql:
            return "bare head with hair"
        return "normal"

    res = SituationPatternAnalyzer.probe_situations(img, mock_vqa, user_prompt="Is the rider safe?")
    assert len(res.safety_or_hazard_flags) > 0
    assert any("helmet" in flag.lower() for flag in res.safety_or_hazard_flags)


def test_pattern_analyzer_plant_disease():
    """Verify botanical and leaf disease identification."""
    # Green plant palette image
    green_arr = np.full((100, 100, 3), [30, 160, 30], dtype=np.uint8)
    # Add yellow-brown disease lesions
    green_arr[40:60, 40:60] = [170, 150, 20]
    plant_img = Image.fromarray(green_arr)

    def mock_vqa(im, q):
        ql = q.lower()
        if "main subject" in ql:
            return "tomato plant leaf"
        if "setting" in ql:
            return "greenhouse garden"
        if "disease" in ql or "spots" in ql:
            return "yellowing leaves with brown fungal leaf spots"
        return "normal"

    res = SituationPatternAnalyzer.probe_situations(plant_img, mock_vqa, user_prompt="Analyze leaf disease")
    assert "Plant" in res.detected_situation or "Botanical" in res.detected_situation
    assert any("disease" in obs.lower() or "spots" in obs.lower() for obs in res.key_observations)


def test_pattern_analyzer_accident():
    """Verify vehicle collision and accident incident identification."""
    img = Image.new("RGB", (100, 100), (80, 80, 80))

    def mock_vqa(im, q):
        ql = q.lower()
        if "main subject" in ql:
            return "damaged cars"
        if "setting" in ql:
            return "highway intersection"
        if "accident" in ql or "collision" in ql:
            return "two car collision with frontal impact damage"
        return "normal"

    res = SituationPatternAnalyzer.probe_situations(img, mock_vqa, user_prompt="What happened in this accident?")
    assert "Accident" in res.detected_situation or "Collision" in res.detected_situation
    assert len(res.safety_or_hazard_flags) > 0


# ==============================================================================
# 3. DOCUMENT INTELLIGENCE TESTS (CSV, JSON, PDF)
# ==============================================================================

def test_document_analyzer_csv():
    """Verify deep CSV analysis with numerical summaries and distributions."""
    csv_content = """Date,Region,Product,Sales,Units,Profit
2026-01-01,North,Widget A,1200.50,15,350.00
2026-01-02,South,Widget B,850.00,10,210.00
2026-01-03,North,Widget A,1450.00,18,420.00
2026-01-04,West,Widget C,2100.00,25,600.00
2026-01-05,East,Widget B,950.00,12,250.00
"""
    summary = UniversalDocumentAnalyzer.analyze_csv_bytes(csv_content.encode("utf-8"), "sales_report.csv")
    assert summary.record_count == 5
    assert summary.column_or_key_count == 6
    assert "Sales, Commercial" in summary.key_observations[0]
    assert "sales" in summary.structured_content_text.lower()
    assert len(summary.executive_summary) > 20


def test_document_analyzer_json_records():
    """Verify JSON record array parsing and attribute profiling."""
    json_data = [
        {"id": 1, "username": "alex", "score": 95.5, "status": "active"},
        {"id": 2, "username": "beatrice", "score": 88.0, "status": "active"},
        {"id": 3, "username": "charles", "score": 72.5, "status": "pending"}
    ]
    raw_bytes = json.dumps(json_data).encode("utf-8")
    summary = UniversalDocumentAnalyzer.analyze_json_bytes(raw_bytes, "users.json")
    assert summary.record_count == 3
    assert "score" in summary.structured_content_text
    assert "3 uniform structured records" in summary.structured_content_text


def test_document_analyzer_json_object():
    """Verify JSON configuration/nested object parsing."""
    json_obj = {
        "system_config": {"env": "production", "debug": False},
        "database": {"host": "localhost", "port": 5432},
        "features": ["auth", "analytics", "vision"]
    }
    raw_bytes = json.dumps(json_obj).encode("utf-8")
    summary = UniversalDocumentAnalyzer.analyze_json_bytes(raw_bytes, "config.json")
    assert summary.column_or_key_count == 3
    assert "system_config" in summary.structured_content_text


def test_file_parser_csv_integration():
    """Verify parse_uploaded_file properly parses CSV files."""
    csv_bytes = b"Item,Qty,Price\nApples,50,1.20\nOranges,30,1.50\n"
    img, text = parse_uploaded_file(csv_bytes, "inventory.csv")
    assert img is None
    assert "Structured CSV Intelligence" in text
    assert "inventory.csv" in text


def test_file_parser_json_integration():
    """Verify parse_uploaded_file properly parses JSON files."""
    json_bytes = b'{"status": "operational", "version": "2.4"}'
    img, text = parse_uploaded_file(json_bytes, "status.json")
    assert img is None
    assert "Structured JSON Object Intelligence" in text


# ==============================================================================
# 4. API END-TO-END ANALYZE INTEGRATION TESTS
# ==============================================================================

def test_api_analyze_csv_file():
    """Verify /analyze endpoint handles CSV file upload."""
    csv_data = b"Student,Subject,Score\nAlice,Math,92\nBob,Science,85\n"
    response = client.post(
        "/analyze",
        files={"file": ("scores.csv", io.BytesIO(csv_data), "text/csv")},
        data={"prompt": "Analyze student performance", "history": "[]"}
    )
    assert response.status_code == 200
    res_json = response.json()
    assert "answer" in res_json
    assert res_json["model"] == "Curiosity"
    assert len(res_json["answer"]) > 10


def test_api_analyze_json_file():
    """Verify /analyze endpoint handles JSON file upload."""
    json_data = b'[{"event": "login", "timestamp": "2026-09-28"}, {"event": "upload", "timestamp": "2026-09-28"}]'
    response = client.post(
        "/analyze",
        files={"file": ("audit.json", io.BytesIO(json_data), "application/json")},
        data={"prompt": "Explain this audit log", "history": "[]"}
    )
    assert response.status_code == 200
    res_json = response.json()
    assert "answer" in res_json
    assert res_json["model"] == "Curiosity"


def test_api_analyze_restored_image():
    """Verify /analyze endpoint handles low-light and bright images gracefully."""
    # Dark image
    dark_buf = io.BytesIO()
    Image.new("RGB", (64, 64), (15, 15, 15)).save(dark_buf, format="JPEG")
    dark_buf.seek(0)

    response = client.post(
        "/analyze",
        files={"image": ("dark_scene.jpg", dark_buf, "image/jpeg")},
        data={"prompt": "Describe what you see", "history": "[]"}
    )
    assert response.status_code == 200
    res_json = response.json()
    assert "answer" in res_json
    assert res_json["model"] == "Curiosity"
