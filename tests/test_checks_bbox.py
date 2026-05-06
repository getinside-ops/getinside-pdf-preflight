"""Tests that CheckResult.bbox is populated where geometric context exists."""

from __future__ import annotations

import io

import fitz
import pytest

from preflight.checks import CheckResult, Severity
from preflight.checks.dimensions import check_dimensions
from preflight.checks.image_resolution import check_image_resolution
from preflight.document import Document, UploadedFile
from preflight.formats import get_format
from tests.conftest import A5_W_PT, A5_H_PT


def test_bbox_none_on_check_result_by_default():
    r = CheckResult(check_name="foo", severity=Severity.INFO, message="ok")
    assert r.bbox is None


def _pdf_with_safe_zone_violation() -> bytes:
    """PDF with text just inside the TrimBox edge (< 3mm safe zone)."""
    bleed_pt = 2.0 / 25.4 * 72.0
    media_w = A5_W_PT + 2 * bleed_pt
    media_h = A5_H_PT + 2 * bleed_pt
    doc = fitz.open()
    page = doc.new_page(width=media_w, height=media_h)
    trim_rect = fitz.Rect(bleed_pt, bleed_pt, bleed_pt + A5_W_PT, bleed_pt + A5_H_PT)
    page.set_trimbox(trim_rect)
    # Place text 1mm (2.83pt) from TrimBox edge — inside the 3mm safe zone
    page.insert_text((trim_rect.x0 + 2.0, trim_rect.y0 + 20.0), "Texte trop proche du bord", fontsize=8)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def test_safe_zone_violation_has_bbox():
    f = UploadedFile(name="close.pdf", data=_pdf_with_safe_zone_violation())
    doc = Document.from_upload([f])
    results = check_dimensions(doc, get_format("A5"))
    violation_results = [
        r for r in results
        if "zone tranquille" in r.message and r.bbox is not None
    ]
    assert violation_results, "safe zone violation CheckResult should have a bbox"
    bbox = violation_results[0].bbox
    assert len(bbox) == 4
    x0, y0, x1, y1 = bbox
    assert x1 > x0 and y1 > y0, "bbox must be non-degenerate"


def _pdf_with_small_image() -> bytes:
    """PDF with a tiny (low effective DPI) embedded image."""
    doc = fitz.open()
    page = doc.new_page(width=A5_W_PT, height=A5_H_PT)
    from PIL import Image as PILImage
    img = PILImage.new("RGB", (10, 10), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    # Insert at 100pt×100pt → effective DPI ≈ (10/100)*72 = 7.2 DPI → ERROR
    page.insert_image(fitz.Rect(50, 50, 150, 150), stream=buf.getvalue())
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def test_low_res_image_has_bbox():
    f = UploadedFile(name="lowres.pdf", data=_pdf_with_small_image())
    doc = Document.from_upload([f])
    results = check_image_resolution(doc)
    error_results = [r for r in results if r.severity is Severity.ERROR]
    assert error_results, "low DPI image must produce an ERROR"
    assert any(r.bbox is not None for r in error_results), (
        "low-res image ERROR CheckResult should carry its bbox on the page"
    )


def test_high_res_pdf_no_images_has_no_bbox():
    """A plain PDF with no embedded images: no image_resolution results with bbox."""
    doc = fitz.open()
    doc.new_page(width=A5_W_PT, height=A5_H_PT)
    out = io.BytesIO()
    doc.save(out)
    f = UploadedFile(name="clean.pdf", data=out.getvalue())
    document = Document.from_upload([f])
    results = check_image_resolution(document)
    assert all(r.bbox is None for r in results)


def test_high_res_image_info_result_has_no_bbox():
    """A page with a genuinely high-res image: INFO result should have bbox=None."""
    from PIL import Image as PILImage
    doc = fitz.open()
    page = doc.new_page(width=A5_W_PT, height=A5_H_PT)
    # 500×500 px image placed at 50×50 pt → DPI ≈ (500/50)*72 = 720 DPI → INFO
    img = PILImage.new("RGB", (500, 500), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    page.insert_image(fitz.Rect(50, 50, 100, 100), stream=buf.getvalue())
    out = io.BytesIO()
    doc.save(out)
    f = UploadedFile(name="highres.pdf", data=out.getvalue())
    document = Document.from_upload([f])
    results = check_image_resolution(document)
    info_results = [r for r in results if r.severity is Severity.INFO]
    assert info_results, "high-DPI image should produce an INFO result"
    assert all(r.bbox is None for r in info_results), (
        "INFO results should not carry bbox (nothing to highlight)"
    )
