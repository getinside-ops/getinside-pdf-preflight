"""Advertiser identification check — auto-detection mode.

Scans the document for mandatory French legal mentions without requiring
any user input:
* Legal form (SAS, SARL, SA, …)
* "Capital social" + amount
* RCS clause: « RCS <city> <9-digit SIREN> »
* French postal code (address presence proxy)

Each element is detected by pattern and reported as INFO (found) or
ERROR/WARNING (missing).
"""

from __future__ import annotations

import re

from preflight.checks import CheckResult, Severity
from preflight.text_normalize import normalize

RCS_RE = re.compile(
    r"rcs\s+([a-z][a-z\-\s]+?)\s+(\d{3}\s?\d{3}\s?\d{3})",
    re.IGNORECASE,
)

# Longest alternatives first to avoid SAS matching inside SASU/SARL.
LEGAL_FORM_RE = re.compile(
    r"\b(selarl|scop|sasu|sarl|eurl|snc|sci|sas|sa)\b",
    re.IGNORECASE,
)

CAPITAL_RE = re.compile(
    r"capital\s+social\s*[:\-]?\s*([\d\s\.,]+\s*(?:euros?|€)?)",
    re.IGNORECASE,
)

POSTAL_CODE_RE = re.compile(r"\b\d{5}\b")


def check_advertiser(all_text: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    norm = normalize(all_text)

    # Legal form
    form_matches = LEGAL_FORM_RE.findall(norm)
    if form_matches:
        unique_forms = list(dict.fromkeys(f.upper() for f in form_matches))
        results.append(
            CheckResult(
                check_name="advertiser",
                severity=Severity.INFO,
                message=f"Forme juridique détectée : {', '.join(unique_forms)}.",
                details={"detected": unique_forms},
            )
        )
    else:
        results.append(
            CheckResult(
                check_name="advertiser",
                severity=Severity.ERROR,
                message="Aucune forme juridique (SAS, SARL, SA…) détectée dans le document.",
            )
        )

    # Capital social
    cap_match = CAPITAL_RE.search(norm)
    if cap_match:
        amount = cap_match.group(1).strip()
        results.append(
            CheckResult(
                check_name="advertiser",
                severity=Severity.INFO,
                message=f"Capital social détecté : {amount}.",
                details={"montant": amount},
            )
        )
    else:
        results.append(
            CheckResult(
                check_name="advertiser",
                severity=Severity.ERROR,
                message="Mention « Capital social » introuvable dans le document.",
            )
        )

    # RCS
    rcs_matches = list(RCS_RE.finditer(norm))
    if rcs_matches:
        for m in rcs_matches:
            city = m.group(1).strip().title()
            siren = re.sub(r"\s+", "", m.group(2))
            results.append(
                CheckResult(
                    check_name="advertiser",
                    severity=Severity.INFO,
                    message=f"RCS détecté : {city} {siren}.",
                    details={"ville": city, "siren": siren},
                )
            )
    else:
        results.append(
            CheckResult(
                check_name="advertiser",
                severity=Severity.ERROR,
                message=(
                    "Mention RCS introuvable. "
                    "Format attendu : « RCS <Ville> <numéro SIREN à 9 chiffres> »."
                ),
            )
        )

    # Address (postal code proxy)
    if POSTAL_CODE_RE.search(all_text):
        results.append(
            CheckResult(
                check_name="advertiser",
                severity=Severity.INFO,
                message="Code postal détecté — adresse du siège présumée présente.",
            )
        )
    else:
        results.append(
            CheckResult(
                check_name="advertiser",
                severity=Severity.WARNING,
                message=(
                    "Aucun code postal détecté — vérifiez manuellement "
                    "l'adresse du siège social."
                ),
            )
        )

    return results


__all__ = ["check_advertiser", "RCS_RE"]
