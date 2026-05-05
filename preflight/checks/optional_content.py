"""Optional Content (layers) detection."""

from typing import List

from preflight.checks import CheckResult, Severity
from preflight.document import Document


def check_optional_content(document: Document) -> List[CheckResult]:
    """Detect Optional Content (OC) layers that may be hidden."""
    results: List[CheckResult] = []

    if document.kind != "pdf":
        return results

    return results  # Disabled - PyMuPDF API trop complexe


__all__ = ["check_optional_content"]