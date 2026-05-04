"""Offer end date + promo code — auto-detection mode.

Scans the document for expiry dates near standard French keywords
(« valable », « jusqu'au », « offre ») and promotional codes after
« code promo ». No user input required.

Findings are reported as INFO; the absence of an expiry date triggers a
WARNING (not an ERROR, since not all campaigns have a limited-time offer).
"""

from __future__ import annotations

import re

from preflight.checks import CheckResult, Severity
from preflight.text_normalize import normalize

# Run on normalized (accent-stripped, lowercase) text.
# Matches dates preceded by expiry keywords. Handles:
#   numeric: 31/12/2026  31-12-2026  31.12.2026
#   text:    31 decembre 2026  1er janvier 2026
EXPIRY_DATE_RE = re.compile(
    r"(?:jusqu'au|valable|offre)\s+(?:jusqu'au\s+)?"
    r"("
    r"\d{1,2}[/\-\.]\d{1,2}[/\-\.](?:\d{4}|\d{2})"
    r"|\d{1,2}(?:er)?\s+"
    r"(?:janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre)"
    r"\.?\s+\d{4}"
    r")",
    re.IGNORECASE,
)

# Run on original text to preserve case.
# Requires "code promo" keyword to avoid false positives on e.g. "code postal".
PROMO_CODE_RE = re.compile(
    r"code\s+promo\s*[:\-–]?\s*([A-Za-z][A-Za-z0-9]{2,19})",
    re.IGNORECASE,
)


def check_offer(all_text: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    norm = normalize(all_text)

    # Expiry dates
    date_matches = list(EXPIRY_DATE_RE.finditer(norm))
    if date_matches:
        dates = list(dict.fromkeys(m.group(1) for m in date_matches))
        for d in dates:
            results.append(
                CheckResult(
                    check_name="offer",
                    severity=Severity.INFO,
                    message=f"Date de fin d'offre détectée : {d}.",
                    details={"date": d},
                )
            )
    else:
        results.append(
            CheckResult(
                check_name="offer",
                severity=Severity.WARNING,
                message=(
                    "Aucune date de fin d'offre détectée. "
                    "Si cette campagne comporte une offre limitée, vérifiez manuellement."
                ),
            )
        )

    # Promo codes
    code_matches = list(PROMO_CODE_RE.finditer(all_text))
    if code_matches:
        codes = list(dict.fromkeys(m.group(1) for m in code_matches))
        for c in codes:
            results.append(
                CheckResult(
                    check_name="offer",
                    severity=Severity.INFO,
                    message=f"Code promo détecté : « {c} ».",
                    details={"code": c},
                )
            )
    else:
        results.append(
            CheckResult(
                check_name="offer",
                severity=Severity.INFO,
                message="Aucun code promo détecté.",
            )
        )

    return results


__all__ = ["check_offer"]
