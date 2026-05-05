"""Shared fixtures: programmatically build small PDFs/images on the fly.

Avoids storing binary fixtures in the repo for the basic structural tests.
The integration tests in test_pipeline_integration.py use richer fixtures
that include drawn QR codes and full advertiser/legal text.
"""

from __future__ import annotations

import io

import fitz
import pytest
from PIL import Image

from preflight.document import UploadedFile

# A5 trim in points (1pt = 25.4/72 mm)
A5_W_PT = 148.0 / 25.4 * 72.0
A5_H_PT = 210.0 / 25.4 * 72.0


def _make_pdf(
    *,
    pages: int = 1,
    width_pt: float = A5_W_PT,
    height_pt: float = A5_H_PT,
    text: str | None = "Hello print preflight",
    encrypt: bool = False,
) -> bytes:
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page(width=width_pt, height=height_pt)
        if text:
            page.insert_text((40, 60), text, fontsize=10)
    if encrypt:
        out = io.BytesIO()
        doc.save(
            out,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="owner",
            user_pw="secret",
        )
        return out.getvalue()
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def _make_png(width_px: int, height_px: int, dpi: int = 300, mode: str = "RGB") -> bytes:
    img = Image.new(mode, (width_px, height_px), color="white" if mode == "RGB" else 255)
    out = io.BytesIO()
    img.save(out, format="PNG", dpi=(dpi, dpi))
    return out.getvalue()


def _make_jpeg(width_px: int, height_px: int, dpi: int = 300, mode: str = "CMYK") -> bytes:
    if mode == "CMYK":
        img = Image.new("CMYK", (width_px, height_px), color=(0, 0, 0, 0))
    else:
        img = Image.new("RGB", (width_px, height_px), color="white")
    out = io.BytesIO()
    img.save(out, format="JPEG", dpi=(dpi, dpi), quality=90)
    return out.getvalue()


def _make_pdf_with_trimbox(
    *,
    trim_w_pt: float = A5_W_PT,
    trim_h_pt: float = A5_H_PT,
    bleed_mm: float = 2.0,
    text: str = "Hello preflight",
    text_margin_pt: float = 40.0,
    add_trim_marks: bool = False,
) -> bytes:
    """PDF with explicit TrimBox and MediaBox set to trimbox + bleed."""
    bleed_pt = bleed_mm / 25.4 * 72.0
    media_w = trim_w_pt + 2 * bleed_pt
    media_h = trim_h_pt + 2 * bleed_pt
    doc = fitz.open()
    page = doc.new_page(width=media_w, height=media_h)
    # Set TrimBox offset by bleed
    trim_rect = fitz.Rect(bleed_pt, bleed_pt, bleed_pt + trim_w_pt, bleed_pt + trim_h_pt)
    page.set_trimbox(trim_rect)
    # Insert text at margin from TrimBox
    page.insert_text(
        (trim_rect.x0 + text_margin_pt, trim_rect.y0 + text_margin_pt),
        text,
        fontsize=10,
    )
    if add_trim_marks:
        # Draw short lines at corners outside TrimBox (simulating Illustrator marks)
        mark_len = 20  # ~7mm
        gap = 5        # gap from trim edge
        shape = page.new_shape()
        # Top-left corner marks
        shape.draw_line(
            fitz.Point(trim_rect.x0 - gap - mark_len, trim_rect.y0),
            fitz.Point(trim_rect.x0 - gap, trim_rect.y0),
        )
        shape.draw_line(
            fitz.Point(trim_rect.x0, trim_rect.y0 - gap - mark_len),
            fitz.Point(trim_rect.x0, trim_rect.y0 - gap),
        )
        shape.finish(color=(0, 0, 0), width=0.5)
        shape.commit()
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


@pytest.fixture
def pdf_a5_single() -> UploadedFile:
    return UploadedFile(name="flyer.pdf", data=_make_pdf(pages=1))


@pytest.fixture
def pdf_a5_recto_verso() -> UploadedFile:
    return UploadedFile(name="flyer.pdf", data=_make_pdf(pages=2))


@pytest.fixture
def pdf_three_pages() -> UploadedFile:
    return UploadedFile(name="flyer.pdf", data=_make_pdf(pages=3))


@pytest.fixture
def pdf_encrypted() -> UploadedFile:
    return UploadedFile(name="locked.pdf", data=_make_pdf(encrypt=True))


@pytest.fixture
def png_a5_300dpi() -> UploadedFile:
    # 148mm @ 300dpi = 1748 px ; 210mm @ 300dpi = 2480 px
    return UploadedFile(name="recto.png", data=_make_png(1748, 2480, dpi=300))


@pytest.fixture
def png_a5_low_dpi() -> UploadedFile:
    # 148mm @ 150dpi = 874 px ; 210mm @ 150dpi = 1240 px
    return UploadedFile(name="recto.png", data=_make_png(874, 1240, dpi=150))


@pytest.fixture
def jpeg_a5_cmyk_300dpi() -> UploadedFile:
    return UploadedFile(name="recto.jpg", data=_make_jpeg(1748, 2480, dpi=300, mode="CMYK"))


@pytest.fixture
def jpeg_a5_rgb_300dpi() -> UploadedFile:
    return UploadedFile(name="recto.jpg", data=_make_jpeg(1748, 2480, dpi=300, mode="RGB"))
