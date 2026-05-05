"""Corrupted PDF objects detection."""

from typing import List

from preflight.checks import CheckResult, Severity
from preflight.document import Document


def check_corrupted_objects(document: Document) -> List[CheckResult]:
    """Detect malformed or corrupted PDF objects."""
    results: List[CheckResult] = []

    if document.kind != "pdf":
        return results

    try:
        fitz_doc = document._fitz_doc
        page_count = len(fitz_doc)

        for page_num in range(page_count):
            try:
                _ = fitz_doc.load_page(page_num)
            except Exception as e:
                results.append(
                    CheckResult(
                        check_name="corrupted_objects",
                        severity=Severity.ERROR,
                        message=f"Page {page_num + 1} potentiellement corrompue: {e}",
                        page=page_num,
                    )
                )
    except Exception as exc:
        results.append(
            CheckResult(
                check_name="corrupted_objects",
                severity=Severity.ERROR,
                message=f"Document potentiellement corrompu: {exc}",
            )
        )

    return results


__all__ = ["check_corrupted_objects"]