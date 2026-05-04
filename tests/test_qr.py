"""QR detection tests using segno-generated fixtures."""

from __future__ import annotations

import io

import pytest
import segno
from PIL import Image

from preflight.qr import detect_qr_codes


def _qr_image(data: str, *, scale: int = 8, border: int = 4) -> Image.Image:
    qr = segno.make(data, error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=scale, border=border)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def _embed_qr_on_canvas(
    qr_img: Image.Image,
    canvas_size_px: tuple[int, int] = (1748, 2480),
    position: tuple[int, int] = (200, 200),
) -> Image.Image:
    canvas = Image.new("RGB", canvas_size_px, "white")
    canvas.paste(qr_img, position)
    return canvas


def test_detects_single_qr():
    qr = _qr_image("https://getinsi.de/HELLO2026", scale=10)
    canvas = _embed_qr_on_canvas(qr)
    detections = detect_qr_codes(canvas, dpi=300)
    assert len(detections) == 1
    assert detections[0].data == "https://getinsi.de/HELLO2026"
    assert detections[0].bbox_mm is not None


def test_returns_empty_when_no_qr():
    canvas = Image.new("RGB", (800, 800), "white")
    detections = detect_qr_codes(canvas, dpi=300)
    assert detections == []


def test_bbox_mm_uses_provided_dpi():
    qr = _qr_image("https://getinsi.de/X", scale=12)
    canvas = _embed_qr_on_canvas(qr)
    detections = detect_qr_codes(canvas, dpi=300)
    assert detections
    # The QR module size + border roughly determines pixel size; the test
    # only verifies that mm = pixels / dpi * 25.4 is consistent.
    d = detections[0]
    px_w = d.bbox_pixels[2]
    expected_mm = px_w / 300.0 * 25.4
    assert d.width_mm == pytest.approx(expected_mm, rel=0.01)


def test_no_dpi_means_no_mm_bbox():
    qr = _qr_image("https://getinsi.de/X", scale=10)
    canvas = _embed_qr_on_canvas(qr)
    detections = detect_qr_codes(canvas, dpi=None)
    assert detections
    assert detections[0].bbox_mm is None
    assert detections[0].short_side_mm is None
