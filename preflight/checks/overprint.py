"""Overprint validation."""

from typing import List

from preflight.checks import CheckResult, Severity
from preflight.document import Document


def check_overprint(document: Document) -> List[CheckResult]:
    """Validate overprint/knockout settings."""
    results: List[CheckResult] = []

    if document.kind != "pdf":
        return results

    return results  # Disabled - PyMuPDF API trop complexe


__all__ = ["check_overprint"]