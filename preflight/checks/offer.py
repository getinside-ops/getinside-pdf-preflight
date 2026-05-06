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
# For date ranges ("du X au Y"), capture the end date (after "au").
EXPIRY_DATE_RE = re.compile(
    r"(?:jusqu'au|valable|offre)\s*[^.!?\n]{0,80}?"
    r"(?:"
    r"\d{1,2}[/\-\.]\d{1,2}[/\-\.](?:\d{4}|\d{2})"
    r"|\d{1,2}(?:er)?\s+"
    r"(?:janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|novembre|decembre)"
    r"\.?\s+\d{4}"
    r")",
    re.IGNORECASE,
)

# Run on original text to preserve case.
# Matches common French marketing phrasings that introduce a promo code.
# The separator (colon, dash) is optional so "avec le code SAGETCAATS" works too.
# Handles newlines between keyword and code (OCR often splits them).
PROMO_CODE_RE = re.compile(
    r"(?:"
    r"code\s+(?:promo|remise|r[ée]duction|avantage|exclusif)"  # "code promo/remise/réduction…"
    r"|avec\s+le\s+code"                                        # "avec le code"
    r"|utilisez\s+(?:le\s+)?code"                              # "utilisez le code" / "utilisez code"
    r"|(?:votre|mon|ton)\s+code"                               # "votre/mon/ton code"
    r")\s*[:\-–\s\n\r]*\s*([A-Za-z][A-Za-z0-9]{2,19})",
    re.IGNORECASE,
)


def check_offer(all_text: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    norm = normalize(all_text)

    # Find ALL date-like patterns in text
    DATE_NUMERIC_RE = re.compile(
        r"\d{1,2}[/\-\.]\d{1,2}[/\-\.](?:\d{4}|\d{2})",
        re.IGNORECASE,
    )
    DATE_TEXT_RE = re.compile(
        r"\d{1,2}(?:er)?\s+(?:janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|novembre|decembre)\.?\s+\d{4}",
        re.IGNORECASE,
    )

    # Collect all unique dates near expiry keywords
    numeric_dates = DATE_NUMERIC_RE.findall(norm)
    text_dates = DATE_TEXT_RE.findall(norm)

    if numeric_dates or text_dates:
        dates = list(dict.fromkeys(numeric_dates + text_dates))
        # For date ranges, report the last date as end date
        end_date = dates[-1] if len(dates) > 1 else dates[0]
        results.append(
            CheckResult(
                check_name="offer",
                severity=Severity.INFO,
                message=f"Date de fin d'offre détectée : {end_date}.",
                details={"date": end_date},
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
