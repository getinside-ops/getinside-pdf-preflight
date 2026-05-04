"""Text extraction with OCR fallback.

Strategy:

1. For PDF pages, try the embedded text layer first. Print-ready PDFs are
   often flattened to outlines (text → vector paths) and return an empty
   or near-empty text layer; in that case we render the page at OCR_DPI
   and run Tesseract.
2. For raster pages (PNG/JPEG uploads), always use OCR.

Tesseract is invoked with `lang='fra'` so French accents survive.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pytesseract
from PIL import Image

from preflight.document import Document, Page

OCR_DPI = 300
TEXT_LAYER_MIN_WORDS = 20
TESSERACT_LANG = "fra"


class ExtractionMethod(str, Enum):
    TEXT_LAYER = "text_layer"
    OCR = "ocr"
    EMPTY = "empty"


@dataclass(frozen=True)
class PageText:
    text: str
    method: ExtractionMethod
    page_index: int


def _ocr(image: Image.Image) -> str:
    try:
        return pytesseract.image_to_string(image, lang=TESSERACT_LANG)
    except pytesseract.TesseractNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "Tesseract OCR n'est pas installé. Voir README pour l'installation."
        ) from exc


def extract_page_text(page: Page) -> PageText:
    if page.source == "image":
        rendered = page.render()
        text = _ocr(rendered)
        method = ExtractionMethod.OCR if text.strip() else ExtractionMethod.EMPTY
        return PageText(text=text, method=method, page_index=page.index)

    # PDF page: try text layer first.
    text = page.text_layer().strip()
    word_count = len(text.split()) if text else 0
    if word_count >= TEXT_LAYER_MIN_WORDS:
        return PageText(text=text, method=ExtractionMethod.TEXT_LAYER, page_index=page.index)

    # Sparse text layer → fall back to OCR on rendered page.
    rendered = page.render(dpi=OCR_DPI)
    ocr_text = _ocr(rendered)
    if ocr_text.strip():
        return PageText(text=ocr_text, method=ExtractionMethod.OCR, page_index=page.index)
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
    "PageText",
    "all_text",
    "extract_document_text",
    "extract_page_text",
]
