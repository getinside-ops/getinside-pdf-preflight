"""Linearized PDF check (optimisation pour affichage web)."""

from typing import List

from preflight.checks import CheckResult, Severity
from preflight.document import Document


def check_linearized(document: Document) -> List[CheckResult]:
    """Check if PDF is linearized for web optimization."""
    results: List[CheckResult] = []

    if document.kind != "pdf":
        return results

    return results  # Disabled - info non pertinente pour impression


__all__ = ["check_linearized"]