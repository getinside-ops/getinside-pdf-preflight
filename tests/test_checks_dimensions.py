"""Tests for dimension checks: TrimBox, bleed, trim marks, safe zone."""

from __future__ import annotations

import io
import fitz
import pytest
from preflight.checks import Severity
from preflight.checks.dimensions import check_dimensions
from preflight.document import Document, UploadedFile
from preflight.formats import get_format
from tests.conftest import A5_W_PT, A5_H_PT, _make_pdf_with_trimbox


def _doc(data: bytes) -> Document:
    return Document.from_upload([UploadedFile(name="test.pdf", data=data)])


def _fmt():
    return get_format("A5")


def test_trim_marks_detected():
    data = _make_pdf_with_trimbox(add_trim_marks=True)
    doc = _doc(data)
    results = check_dimensions(doc, _fmt())
    assert any("traits de coupe" in r.message for r in results)


def test_no_trim_marks_no_mark_message():
    data = _make_pdf_with_trimbox(add_trim_marks=False)
    doc = _doc(data)
    results = check_dimensions(doc, _fmt())
    assert not any("traits de coupe" in r.message for r in results)


def test_safe_zone_respected_when_text_centered():
    # Text at 40pt margin from TrimBox edge; safe zone is 3mm = ~8.5pt
    data = _make_pdf_with_trimbox(text_margin_pt=40.0)
    doc = _doc(data)
    results = check_dimensions(doc, _fmt())
    assert any("zone tranquille respectée" in r.message for r in results)
    assert not any("zone tranquille" in r.message and r.severity is Severity.WARNING for r in results)


def test_safe_zone_violated_when_text_near_edge():
    # Text at 2pt margin (~0.7mm) from TrimBox edge, well inside safe zone
    data = _make_pdf_with_trimbox(text_margin_pt=2.0)
    doc = _doc(data)
    results = check_dimensions(doc, _fmt())
    assert any(
        "zone tranquille" in r.message and r.severity is Severity.WARNING
        for r in results
    )
