"""Tests for the visual checks (dimensions, colorspace, qrcode)."""

from __future__ import annotations

import io

import fitz
import pytest
import segno
from PIL import Image

from preflight.checks import Severity
from preflight.checks.colorspace import check_colorspace
from preflight.checks.dimensions import check_dimensions
from preflight.checks.qrcode import check_qr
from preflight.document import Document, UploadedFile
from preflight.formats import custom_format, get_format
from tests.conftest import A5_H_PT, A5_W_PT


def _has_error(results) -> bool:
    return any(r.severity is Severity.ERROR for r in results)


# --- Dimensions ---------------------------------------------------------------


def test_dimensions_a5_pdf_compliant(pdf_a5_single):
    doc = Document.from_upload([pdf_a5_single])
    results = check_dimensions(doc, get_format("A5"))
    assert not _has_error(results)


def test_dimensions_undersized_pdf():
    # Build an undersized PDF (A6 instead of A5)
    d = fitz.open()
    d.new_page(width=105 / 25.4 * 72.0, height=148 / 25.4 * 72.0)
    out = io.BytesIO()
    d.save(out)
    f = UploadedFile(name="undersized.pdf", data=out.getvalue())
    doc = Document.from_upload([f])
    results = check_dimensions(doc, get_format("A5"))
    assert _has_error(results)


def test_dimensions_image_low_dpi(png_a5_low_dpi):
    doc = Document.from_upload([png_a5_low_dpi])
    results = check_dimensions(doc, get_format("A5"))
    # 150 DPI: dimensions still match A5 in mm, but DPI < 300 → error.
    assert _has_error(results)


def test_dimensions_custom_format(pdf_a5_single):
    doc = Document.from_upload([pdf_a5_single])
    spec = custom_format(148.0, 210.0)
    results = check_dimensions(doc, spec)
    assert not _has_error(results)


# --- Colorspace ---------------------------------------------------------------


def test_colorspace_jpeg_cmyk_compliant(jpeg_a5_cmyk_300dpi):
    doc = Document.from_upload([jpeg_a5_cmyk_300dpi])
    results = check_colorspace(doc)
    assert not _has_error(results)


def test_colorspace_jpeg_rgb_errors(jpeg_a5_rgb_300dpi):
    doc = Document.from_upload([jpeg_a5_rgb_300dpi])
    results = check_colorspace(doc)
    assert _has_error(results)


def test_colorspace_png_warning(png_a5_300dpi):
    doc = Document.from_upload([png_a5_300dpi])
    results = check_colorspace(doc)
    severities = {r.severity for r in results}
    assert Severity.WARNING in severities
    assert not _has_error(results)


def test_colorspace_advisory_always_present(pdf_a5_single):
    doc = Document.from_upload([pdf_a5_single])
    results = check_colorspace(doc)
    assert any("encrage" in r.message for r in results)


# --- QR code ------------------------------------------------------------------


def _make_pdf_with_qr_image(qr_url: str, qr_size_px: int = 320) -> bytes:
    """A5 PDF with a QR PNG embedded as a raster image."""
    qr = segno.make(qr_url, error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=10, border=1)
    qr_png_bytes = buf.getvalue()

    doc = fitz.open()
    page = doc.new_page(width=A5_W_PT, height=A5_H_PT)
    # 25 mm ≈ 70.87 pt → place a 80pt × 80pt QR (~28 mm) so it passes the
    # min-size check by default.
    rect = fitz.Rect(50, 50, 50 + 80, 50 + 80)
    page.insert_image(rect, stream=qr_png_bytes)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def test_qr_compliant():
    f = UploadedFile(name="ok.pdf", data=_make_pdf_with_qr_image("https://gtinsi.de/HELLO"))
    doc = Document.from_upload([f])
    results = check_qr(doc)
    assert not _has_error(results)
    assert any(r.severity is Severity.INFO and "QR code détecté" in r.message for r in results)


def test_qr_wrong_url_error():
    f = UploadedFile(name="bad.pdf", data=_make_pdf_with_qr_image("https://example.com/HELLO"))
    doc = Document.from_upload([f])
    results = check_qr(doc)
    assert _has_error(results)


def test_qr_missing(pdf_a5_single):
    doc = Document.from_upload([pdf_a5_single])
    results = check_qr(doc)
    assert _has_error(results)


def test_qr_too_small():
    # Tiny QR: place at small pt size
    qr = segno.make("https://gtinsi.de/X", error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=4, border=1)
    qr_png = buf.getvalue()

    d = fitz.open()
    page = d.new_page(width=A5_W_PT, height=A5_H_PT)
    # 40pt ≈ 14 mm — below 25 mm minimum
    page.insert_image(fitz.Rect(50, 50, 90, 90), stream=qr_png)
    out = io.BytesIO()
    d.save(out)
    f = UploadedFile(name="tiny.pdf", data=out.getvalue())
    doc = Document.from_upload([f])
    results = check_qr(doc)
    assert any("trop petit" in r.message for r in results)
