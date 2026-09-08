"""
tests/test_doc_generator.py — Tests for doc_generator.py

Run:
    pytest tests/test_doc_generator.py -v
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pathlib import Path
import tempfile, shutil

# Patch settings.output_dir to use temp dir for tests
import config as _cfg

@pytest.fixture(autouse=True)
def tmp_output(tmp_path, monkeypatch):
    monkeypatch.setattr(_cfg.settings, "output_dir", tmp_path)
    yield tmp_path


from doc_generator import generate_docx, generate_pptx, generate_xlsx


class TestDocx:
    def test_approval_note_creates_file(self):
        content = {
            "title": "Test Approval Note",
            "summary": "Valve inspection passed all checks.",
            "findings": ["Wall thickness OK", "No visible corrosion"],
            "recommendation": "Return to service.",
            "access_level": "department",
        }
        path = generate_docx("approval_note", content, filename="test_approval")
        assert path.exists()
        assert path.suffix == ".docx"
        assert path.stat().st_size > 0

    def test_generic_report_creates_file(self):
        content = {
            "title": "Test Report",
            "sections": [{"heading": "Introduction", "body": "Test body text."}],
        }
        path = generate_docx("generic_report", content, filename="test_report")
        assert path.exists()

    def test_invalid_template_raises(self):
        with pytest.raises(ValueError, match="Unknown DOCX template"):
            generate_docx("nonexistent_template", {})


class TestPptx:
    def test_findings_deck_creates_file(self):
        content = {
            "title": "Inspection Findings",
            "findings": [
                {"heading": "Finding 1", "body": "Valve flange worn."},
                {"heading": "Finding 2", "body": "O-ring scored."},
            ],
        }
        path = generate_pptx("findings_deck", content, filename="test_deck")
        assert path.exists()
        assert path.suffix == ".pptx"

    def test_invalid_template_raises(self):
        with pytest.raises(ValueError):
            generate_pptx("bad_template", {})


class TestXlsx:
    def test_data_table_creates_file(self):
        content = {
            "title": "Equipment Status Table",
            "headers": ["Asset", "Status", "Last Inspected"],
            "rows": [
                ["Valve 7", "OK", "2026-08-15"],
                ["Pump P-105", "FAIL", "2026-08-22"],
            ],
        }
        path = generate_xlsx("data_table", content, filename="test_table")
        assert path.exists()
        assert path.suffix == ".xlsx"

    def test_calculation_sheet_creates_file(self):
        content = {
            "title": "Pump Power Calculation",
            "inputs": [
                {"label": "Flow rate", "value": 50, "unit": "m³/h"},
                {"label": "Head",      "value": 30, "unit": "m"},
                {"label": "Efficiency","value": 0.75,"unit": "-"},
            ],
            "results": [
                {"label": "Hydraulic power", "value": 5.45, "unit": "kW"},
                {"label": "Shaft power",     "value": 7.27, "unit": "kW"},
            ],
        }
        path = generate_xlsx("calculation_sheet", content, filename="test_calc")
        assert path.exists()

    def test_invalid_template_raises(self):
        with pytest.raises(ValueError):
            generate_xlsx("bad_template", {})
