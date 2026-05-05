"""Text extraction with OCR fallback.

Strategy:

1. For PDF pages, try the embedded text layer first. Print-ready PDFs are
   often flattened to outlines (text → vector paths) and return an empty
   or near-empty text layer; in that case we render the page at OCR_DPI
   and run Tesseract.
2. For raster pages (PNG/JPEG uploads), always use OCR.

Tesseract is invoked with `lang='fra'` so French accents survive.

OCR improvements for small legal text:
- Higher DPI (600) for better resolution of small text
- Image preprocessing (CLAHE, grayscale) to enhance text contrast
- Optimized PSM configuration for better text block detection
"""

from __future__ import annotations

import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum

import pytesseract
from PIL import Image

from preflight.document import Document, Page

OCR_DPI = 600
TEXT_LAYER_MIN_WORDS = 20
TESSERACT_LANG = "fra"
TESSERACT_CONFIG = "--psm 6"


class ExtractionMethod(str, Enum):
    TEXT_LAYER = "text_layer"
    OCR = "ocr"
    EMPTY = "empty"


@dataclass(frozen=True)
class OcrSettings:
    dpi: int
    lang: str
    config: str
    preprocessing: tuple[str, ...]


OCR_SETTINGS = OcrSettings(
    dpi=OCR_DPI,
    lang=TESSERACT_LANG,
    config=TESSERACT_CONFIG,
    preprocessing=("grayscale", "CLAHE", "sharpening"),
)


@dataclass(frozen=True)
class PageText:
    text: str
    method: ExtractionMethod
    page_index: int
    ocr_settings_used: OcrSettings | None = None


def _preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """Enhance image for better OCR of small text.

    Applies:
    - Grayscale conversion
    - CLAHE (Contrast Limited Adaptive Histogram Equalization) for enhanced text contrast
    - Light sharpening to improve text edge definition
    """
    img = np.array(image)
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharpened = cv2.filter2D(enhanced, -1, kernel)
    return Image.frombytes("L", (sharpened.shape[1], sharpened.shape[0]), sharpened)


def _ocr(image: Image.Image) -> str:
    try:
        processed = _preprocess_for_ocr(image)
        return pytesseract.image_to_string(
            processed, lang=TESSERACT_LANG, config=TESSERACT_CONFIG
        )
    except pytesseract.TesseractNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "Tesseract OCR n'est pas installé. Voir README pour l'installation."
        ) from exc


def extract_page_text(page: Page) -> PageText:
    if page.source == "image":
        rendered = page.render()
        text = _ocr(rendered)
        method = ExtractionMethod.OCR if text.strip() else ExtractionMethod.EMPTY
        return PageText(
            text=text,
            method=method,
            page_index=page.index,
            ocr_settings_used=OCR_SETTINGS if method == ExtractionMethod.OCR else None,
        )

    # PDF page: try text layer first.
    text = page.text_layer().strip()
    word_count = len(text.split()) if text else 0
    if word_count >= TEXT_LAYER_MIN_WORDS:
        return PageText(text=text, method=ExtractionMethod.TEXT_LAYER, page_index=page.index)

    # Sparse text layer → fall back to OCR on rendered page.
    rendered = page.render(dpi=OCR_DPI)
    ocr_text = _ocr(rendered)
    if ocr_text.strip():
        return PageText(
            text=ocr_text,
            method=ExtractionMethod.OCR,
            page_index=page.index,
            ocr_settings_used=OCR_SETTINGS,
        )
    # OCR also empty: return whatever we had from the text layer (possibly empty).
    return PageText(
        text=text,
        method=ExtractionMethod.TEXT_LAYER if text else ExtractionMethod.EMPTY,
        page_index=page.index,
    )


def extract_document_text(document: Document) -> list[PageText]:
    return [extract_page_text(p) for p in document.pages]


def all_text(document: Document) -> str:
    """Concatenate text from every page (recto-verso aware)."""
    return "\n\n".join(pt.text for pt in extract_document_text(document))


__all__ = [
    "ExtractionMethod",
    "OCR_DPI",
    "OCR_SETTINGS",
    "OcrSettings",
    "PageText",
    "all_text",
    "extract_document_text",
    "extract_page_text",
]
