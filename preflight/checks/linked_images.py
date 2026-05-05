"""Linked images verification."""

from typing import List

from preflight.checks import CheckResult, Severity
from preflight.document import Document


def check_linked_images(document: Document) -> List[CheckResult]:
    """Check for missing or broken image references."""
    results: List[CheckResult] = []

    if document.kind != "pdf":
        return results

    try:
        fitz_doc = document._fitz_doc
        for page_num, page in enumerate(fitz_doc):
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                try:
                    _ = fitz_doc.extract_image(xref)
                except Exception:
                    results.append(
                        CheckResult(
                            check_name="linked_images",
                            severity=Severity.ERROR,
                            message=f"Image corrompue ou manquante à l'index {img_index}",
                            details={"page": page_num + 1, "image_index": img_index, "xref": xref},
                            page=page_num,
                        )
                    )
    except Exception as exc:
        results.append(
            CheckResult(
                check_name="linked_images",
                severity=Severity.WARNING,
                message=f"Impossible de vérifier les images: {exc}",
            )
        )

    return results


__all__ = ["check_linked_images"]