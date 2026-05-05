"""Bleed detection - verifies background extends beyond trim box."""

from __future__ import annotations

from preflight.checks import CheckResult, Severity
from preflight.document import Document

MIN_BLEED_MM = 2.0
TOLERANCE_MM = 0.5


def check_bleed(document: Document) -> list[CheckResult]:
    results: list[CheckResult] = []

    for page in document.pages:
        media = page.media_box_mm()
        trim = page.trim_box_mm()

        if media is None or trim is None:
            continue

        bleed_w = (media.width - trim.width) / 2
        bleed_h = (media.height - trim.height) / 2

        min_bleed = min(bleed_w, bleed_h)

        if min_bleed < MIN_BLEED_MM - TOLERANCE_MM:
            severity = Severity.ERROR
            msg = (
                f"Page {page.index + 1}: fond perdu insuffisant "
                f"({min_bleed:.1f}mm, attendu >= {MIN_BLEED_MM}mm)"
            )
        elif min_bleed < MIN_BLEED_MM:
            severity = Severity.WARNING
            msg = f"Page {page.index + 1}: fond perdu limite ({min_bleed:.1f}mm)"
        else:
            severity = Severity.INFO
            msg = f"Page {page.index + 1}: fond perdu OK ({min_bleed:.1f}mm)"

        results.append(
            CheckResult(
                check_name="bleed",
                severity=severity,
                message=msg,
                details={"bleed_mm": round(min_bleed, 2)},
                page=page.index,
            )
        )

    return results