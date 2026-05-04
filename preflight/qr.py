"""QR-code detection.

Uses OpenCV's built-in `QRCodeDetector.detectAndDecodeMulti`. No system
dependency on `zbar`, which keeps the Streamlit Cloud setup simple.

Returns the decoded URL plus a bounding box in both pixels and millimetres.
The mm conversion requires either a known DPI (raster page) or the DPI
used for rendering (PDF page rendered at OCR_DPI). The caller must pass
the correct DPI value.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class QRDetection:
    data: str
    bbox_pixels: tuple[float, float, float, float]  # x, y, w, h
    bbox_mm: tuple[float, float] | None  # (width_mm, height_mm) — None if dpi unknown

    @property
    def width_mm(self) -> float | None:
        return self.bbox_mm[0] if self.bbox_mm else None

    @property
    def height_mm(self) -> float | None:
        return self.bbox_mm[1] if self.bbox_mm else None

    @property
    def short_side_mm(self) -> float | None:
        return min(self.bbox_mm) if self.bbox_mm else None


def _to_bgr_array(image: Image.Image) -> np.ndarray:
    if image.mode == "CMYK":
        image = image.convert("RGB")
    elif image.mode != "RGB":
        image = image.convert("RGB")
    arr = np.array(image)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def detect_qr_codes(image: Image.Image, dpi: float | None) -> list[QRDetection]:
    """Detect QR codes; bbox in mm is computed only when ``dpi`` is given."""
    bgr = _to_bgr_array(image)
    detector = cv2.QRCodeDetector()
    ok, decoded, points, _ = detector.detectAndDecodeMulti(bgr)
    if not ok or points is None:
        return []

    detections: list[QRDetection] = []
    for data, quad in zip(decoded, points):
        if not data:
            # cv2 sometimes detects geometry but fails to decode.
            continue
        xs = [p[0] for p in quad]
        ys = [p[1] for p in quad]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        w_px = float(x_max - x_min)
        h_px = float(y_max - y_min)
        bbox_mm: tuple[float, float] | None
        if dpi and dpi > 0:
            bbox_mm = (w_px / dpi * 25.4, h_px / dpi * 25.4)
        else:
            bbox_mm = None
        detections.append(
            QRDetection(
                data=data,
                bbox_pixels=(float(x_min), float(y_min), w_px, h_px),
                bbox_mm=bbox_mm,
            )
        )
    return detections


__all__ = ["QRDetection", "detect_qr_codes"]
