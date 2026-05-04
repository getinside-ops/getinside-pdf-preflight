"""Tests for text extraction.

OCR-dependent tests are skipped if Tesseract is not on the host.
"""

from __future__ import annotations

import io
import shutil

import fitz
import pytest
from PIL import Image, ImageDraw, ImageFont

from preflight.document import Document, UploadedFile
from preflight.extract import (
    ExtractionMethod,
    extract_document_text,
    extract_page_text,
)
from tests.conftest import A5_H_PT, A5_W_PT


tesseract_available = shutil.which("tesseract") is not None
needs_tesseract = pytest.mark.skipif(
    not tesseract_available, reason="tesseract not installed on host"
)

LONG_TEXT = (
    "Getinside SAS au capital de 50 000 euros. "
    "Siège social: 12 rue de l'Exemple, 75001 Paris. "
    "RCS Paris 123 456 789. "
    "Offre valable jusqu'au 31/12/2026. "
    "Pour votre santé, mangez au moins cinq fruits et légumes par jour. "
    "Code promo: HELLO2026. "
)


def _pdf_with_long_text() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=A5_W_PT, height=A5_H_PT)
    # Wrap text into multiple lines so the text layer has > 20 words.
    y = 80
    for line in LONG_TEXT.split(". "):
        if line.strip():
            page.insert_text((40, y), line.strip() + ".", fontsize=10)
            y += 14
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def _pdf_blank() -> bytes:
    """No text at all → simulates a flattened/outlined PDF."""
    doc = fitz.open()
    doc.new_page(width=A5_W_PT, height=A5_H_PT)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def _png_with_drawn_text(text: str) -> bytes:
    img = Image.new("RGB", (1748, 2480), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", 36
        )
    except Exception:
        font = ImageFont.load_default()
    y = 200
    for line in text.split(". "):
        if line.strip():
            draw.text((100, y), line.strip() + ".", fill="black", font=font)
            y += 60
    out = io.BytesIO()
    img.save(out, format="PNG", dpi=(300, 300))
    return out.getvalue()


def test_pdf_with_text_layer_uses_text_layer():
    f = UploadedFile(name="rich.pdf", data=_pdf_with_long_text())
    doc = Document.from_upload([f])
    pt = extract_page_text(doc.pages[0])
    assert pt.method == ExtractionMethod.TEXT_LAYER
    assert "Getinside" in pt.text
    assert "RCS Paris" in pt.text


@needs_tesseract
def test_blank_pdf_falls_back_to_ocr_or_empty():
    f = UploadedFile(name="blank.pdf", data=_pdf_blank())
    doc = Document.from_upload([f])
    pt = extract_page_text(doc.pages[0])
    # Blank page → either OCR returns nothing (EMPTY) or text-layer empty.
    assert pt.method in {ExtractionMethod.EMPTY, ExtractionMethod.TEXT_LAYER}
    assert pt.text.strip() == ""


@needs_tesseract
def test_image_uses_ocr():
    data = _png_with_drawn_text(LONG_TEXT)
    f = UploadedFile(name="recto.png", data=data)
    doc = Document.from_upload([f])
    pt = extract_page_text(doc.pages[0])
    assert pt.method == ExtractionMethod.OCR
    # OCR should at least catch the company name and code (case-insensitive)
    lower = pt.text.lower()
    assert "getinside" in lower or "hello2026" in lower


def test_extract_document_text_walks_all_pages(pdf_a5_recto_verso):
    doc = Document.from_upload([pdf_a5_recto_verso])
    pts = extract_document_text(doc)
    assert len(pts) == 2
    assert pts[0].page_index == 0 and pts[1].page_index == 1
