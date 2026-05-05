"""Metadata detection for stripping recommendation."""

from typing import List

from preflight.checks import CheckResult, Severity
from preflight.document import Document

_SENSITIVE_FIELDS = {
    "author",
    "creator",
    "producer",
    "title",
    "subject",
    "keywords",
    "createDate",
    "modDate",
    "trapped",
}


def check_metadata_stripping(document: Document) -> List[CheckResult]:
    """Detect metadata that should be stripped for privacy."""
    results: List[CheckResult] = []

    if document.kind != "pdf":
        return results

    try:
        fitz_doc = document._fitz_doc
        metadata = fitz_doc.metadata

        if not metadata:
            return results

        found_fields = []
        for field in _SENSITIVE_FIELDS:
            value = metadata.get(field)
            if value:
                found_fields.append(field)

        if found_fields:
            results.append(
                CheckResult(
                    check_name="metadata_stripping",
                    severity=Severity.INFO,
                    message=f"Métadonnées détectées: {', '.join(found_fields)}",
                    details={"fields": found_fields},
                )
            )
    except Exception as exc:
        results.append(
            CheckResult(
                check_name="metadata_stripping",
                severity=Severity.WARNING,
                message=f"Impossible de vérifier les métadonnées: {exc}",
            )
        )

    return results


__all__ = ["check_metadata_stripping"]