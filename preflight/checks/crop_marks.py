"""Crop and registration marks detection."""

from typing import List

from preflight.checks import CheckResult, Severity
from preflight.document import Document

_MARK_PATTERNS = ["CropBox", "ArtBox", "BleedBox", "TrimBox"]


def check_crop_marks(document: Document) -> List[CheckResult]:
    """Detect crop, registration, or trim marks."""
    results: List[CheckResult] = []

    if document.kind != "pdf":
        return results

    try:
        fitz_doc = document._fitz_doc
        for page_num, page in enumerate(fitz_doc):
            mediabox = page.mediabox
            for pattern in _MARK_PATTERNS:
                box = getattr(page, pattern, None)
                if box and box != mediabox:
                    results.append(
                        CheckResult(
                            check_name="crop_marks",
                            severity=Severity.INFO,
                            message=f"Boîte {pattern} détectée sur la page {page_num + 1}",
                            details={"box": pattern, "page": page_num + 1},
                            page=page_num,
                        )
                    )
    except Exception as exc:
        results.append(
            CheckResult(
                check_name="crop_marks",
                severity=Severity.WARNING,
                message=f"Impossible de vérifier les marques: {exc}",
            )
        )

    return results


__all__ = ["check_crop_marks"]