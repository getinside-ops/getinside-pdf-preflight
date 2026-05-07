"""Tests for DocumentSnapshot build and caching."""

from __future__ import annotations

import io

import fitz
import pytest
from PIL import Image

from preflight.document import Document, UploadedFile
from preflight.snapshot import DocumentSnapshot
from tests.conftest import A5_W_PT, A5_H_PT, _make_pdf


def test_snapshot_build_pdf_has_renders():
    f = UploadedFile(name="flyer.pdf", data=_make_pdf(pages=1))
    doc = Document.from_upload([f])
    snap = DocumentSnapshot.build(doc)
    img = snap.get_page_render(0)
    assert isinstance(img, Image.Image)


def test_snapshot_build_two_page_pdf():
    f = UploadedFile(name="flyer.pdf", data=_make_pdf(pages=2))
    doc = Document.from_upload([f])
    snap = DocumentSnapshot.build(doc)
    assert set(snap.page_image_info.keys()) == {0, 1}
    assert set(snap.page_fonts.keys()) == {0, 1}
    assert snap.get_page_render(0)
    assert snap.get_page_render(1)


def test_snapshot_build_image_doc(png_a5_300dpi):
    doc = Document.from_upload([png_a5_300dpi])
    snap = DocumentSnapshot.build(doc)
    assert snap.get_page_render(0)
    # Image pages: page_fonts and page_image_info are empty (PDF-only)
    assert 0 not in snap.page_fonts


def test_snapshot_page_renders_are_300dpi():
    """PDF pages should be rendered at 300 DPI: A5 = ~1748x2480 px."""
    f = UploadedFile(name="flyer.pdf", data=_make_pdf(pages=1))
    doc = Document.from_upload([f])
    snap = DocumentSnapshot.build(doc)
    img = snap.get_page_render(0)
    w, h = img.size
    assert 1700 < w < 1800, f"width {w}px expected ~1748px for A5 at 300dpi"
    assert 2400 < h < 2560, f"height {h}px expected ~2480px for A5 at 300dpi"


def test_snapshot_page_image_info_populated_for_embedded_image():
    """page_image_info should be a non-empty list for PDF pages with embedded images."""
    from PIL import Image as PILImage
    img = PILImage.new("RGB", (50, 50), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    fitz_doc = fitz.open()
    page = fitz_doc.new_page(width=A5_W_PT, height=A5_H_PT)
    page.insert_image(fitz.Rect(50, 50, 100, 100), stream=buf.getvalue())
    pdf_buf = io.BytesIO()
    fitz_doc.save(pdf_buf)
    f = UploadedFile(name="with_image.pdf", data=pdf_buf.getvalue())
    doc = Document.from_upload([f])
    snap = DocumentSnapshot.build(doc)
    assert 0 in snap.page_image_info, "page 0 should be in page_image_info"
    assert len(snap.page_image_info[0]) > 0, "should have at least one image info entry"
    first_info = snap.page_image_info[0][0]
    assert "width" in first_info
    assert "bbox" in first_info
