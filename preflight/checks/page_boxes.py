"""Page boxes validation (TrimBox, BleedBox)."""

from typing import List

from preflight.checks import CheckResult, Severity
from preflight.document import Document


def check_page_boxes(document: Document) -> List[CheckResult]:
    """Validate TrimBox and BleedBox presence."""
    results: List[CheckResult] = []

    if document.kind != "pdf":
        return results

    try:
        fitz_doc = document._fitz_doc
        for page_num, page in enumerate(fitz_doc):
            mediabox = page.mediabox
            page_rect = page.rect

            # Check for trimbox via getattr
            trimbox = getattr(page, "trimbox", None)
            if trimbox is None:
                results.append(
                    CheckResult(
                        check_name="page_boxes",
                        severity=Severity.WARNING,
                        message="TrimBox manquant sur la page (le MediaBox sera utilisé comme taille finale)",
                        details={"page": page_num + 1},
                        page=page_num,
                    )
                )
            elif abs(trimbox.width - mediabox.width) < 1 and abs(trimbox.height - mediabox.height) < 1:
                # TrimBox same as MediaBox - this is actually fine if no bleed
                pass  # No warning needed

            # Check for bleedbox
            bleedbox = getattr(page, "bleedbox", None)
            if bleedbox and (abs(bleedbox.width - mediabox.width) > 1 or abs(bleedbox.height - mediabox.height) > 1):
                results.append(
                    CheckResult(
                        check_name="page_boxes",
                        severity=Severity.INFO,
                        message=f"BleedBox détectée ({bleedbox.width:.1f} × {bleedbox.height:.1f} mm)",
                        details={"page": page_num + 1},
                        page=page_num,
                    )
                )

    except Exception as exc:
        results.append(
            CheckResult(
                check_name="page_boxes",
                severity=Severity.WARNING,
                message=f"Impossible de vérifier les boîtes: {exc}",
            )
        )

    return results


__all__ = ["check_page_boxes"]