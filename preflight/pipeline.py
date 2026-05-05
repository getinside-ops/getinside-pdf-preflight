"""Pipeline orchestrator.

Holds the user-supplied form context and runs every check in sequence,
returning a flat list of `CheckResult`s. The Streamlit layer groups
them by severity for display.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from preflight.checks import CheckResult, Severity
from preflight.checks.advertiser import check_advertiser
from preflight.checks.bleed import check_bleed
from preflight.checks.colorspace import check_colorspace
from preflight.checks.contrast import check_contrast
from preflight.checks.dimensions import check_dimensions
from preflight.checks.font_embedding import check_font_embedding
from preflight.checks.image_resolution import check_image_resolution
from preflight.checks.industry import check_industry
from preflight.checks.linked_images import check_linked_images
from preflight.checks.logos import check_logos
from preflight.checks.offer import check_offer
from preflight.checks.page_boxes import check_page_boxes
from preflight.checks.printer import check_printer
from preflight.checks.qrcode import check_qr
from preflight.checks.spot_colors import check_spot_colors
from preflight.checks.transparency import check_transparency
from preflight.document import Document
from preflight.extract import OCR_SETTINGS, OcrSettings, PageText, all_text, extract_document_text
from preflight.formats import FormatSpec
from preflight.logos import LogoLibrary

PrintMethod = Literal["Imprimé par getinside", "Imprimé par la marque"]

LOGO_LIBRARY_ROOT = Path(__file__).resolve().parent.parent / "assets" / "logos"


@dataclass
class CheckContext:
    format_spec: FormatSpec
    industry: str
    print_method: PrintMethod


@dataclass(frozen=True)
class ExtractionInfo:
    pages: list[PageText]
    ocr_settings: OcrSettings
    text_used: str


def run_all_checks(
    document: Document,
    context: CheckContext,
    *,
    logo_library: LogoLibrary | None = None,
) -> list[CheckResult]:
    if logo_library is None:
        logo_library = LogoLibrary(LOGO_LIBRARY_ROOT)

    results: list[CheckResult] = []
    results.extend(check_dimensions(document, context.format_spec))
    results.extend(check_bleed(document))
    results.extend(check_colorspace(document))
    results.extend(check_image_resolution(document))
    results.extend(check_transparency(document))
    results.extend(check_qr(document))
    results.extend(check_contrast(document))
    results.extend(
        check_logos(document, logo_library, context.print_method)
    )

    # New print preflight checks (utiles uniquement)
    results.extend(check_font_embedding(document))
    results.extend(check_linked_images(document))
    results.extend(check_spot_colors(document))
    results.extend(check_page_boxes(document))

    document_text = all_text(document)

    results.extend(check_advertiser(document_text))
    results.extend(check_offer(document_text))
    results.extend(check_printer(document_text, context.print_method))
    results.extend(check_industry(document_text, context.industry))

    return results


def run_all_checks_with_extraction(
    document: Document,
    context: CheckContext,
    *,
    logo_library: LogoLibrary | None = None,
) -> tuple[list[CheckResult], ExtractionInfo]:
    if logo_library is None:
        logo_library = LogoLibrary(LOGO_LIBRARY_ROOT)

    results: list[CheckResult] = []
    results.extend(check_dimensions(document, context.format_spec))
    results.extend(check_bleed(document))
    results.extend(check_colorspace(document))
    results.extend(check_image_resolution(document))
    results.extend(check_transparency(document))
    results.extend(check_qr(document))
    results.extend(check_contrast(document))
    results.extend(
        check_logos(document, logo_library, context.print_method)
    )

    # New print preflight checks (utiles uniquement)
    results.extend(check_font_embedding(document))
    results.extend(check_linked_images(document))
    results.extend(check_spot_colors(document))
    results.extend(check_page_boxes(document))

    page_texts = extract_document_text(document)
    document_text = all_text(document)

    results.extend(check_advertiser(document_text))
    results.extend(check_offer(document_text))
    results.extend(check_printer(document_text, context.print_method))
    results.extend(check_industry(document_text, context.industry))

    ocr_settings = OCR_SETTINGS
    for pt in page_texts:
        if pt.ocr_settings_used is not None:
            ocr_settings = pt.ocr_settings_used
            break

    extraction_info = ExtractionInfo(
        pages=page_texts,
        ocr_settings=ocr_settings,
        text_used=document_text,
    )

    return results, extraction_info


def summarize(results: list[CheckResult]) -> dict[str, int]:
    counts = {Severity.ERROR: 0, Severity.WARNING: 0, Severity.INFO: 0}
    for r in results:
        counts[r.severity] += 1
    return {s.value: c for s, c in counts.items()}


def overall_verdict(results: list[CheckResult]) -> Literal["pass", "review", "fail"]:
    counts = summarize(results)
    if counts.get(Severity.ERROR.value, 0) > 0:
        return "fail"
    if counts.get(Severity.WARNING.value, 0) > 0:
        return "review"
    return "pass"


__all__ = [
    "CheckContext",
    "ExtractionInfo",
    "LOGO_LIBRARY_ROOT",
    "PrintMethod",
    "overall_verdict",
    "run_all_checks",
    "run_all_checks_with_extraction",
    "summarize",
]
