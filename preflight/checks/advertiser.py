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
    r"rcs\s*:?\s*([a-z][a-z\-\s]+?)\s+[a-z]?\s*(\d{3}\s?\d{3}\s?\d{3})",
    re.IGNORECASE,
)


def _luhn_checksum(siren: str) -> int:
    digits = [int(d) for d in siren]
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    return sum(digits) % 10


def validate_siren(siren: str) -> bool:
    siren = re.sub(r"\s+", "", siren)
    if not siren.isdigit() or len(siren) != 9:
        return False
    return _luhn_checksum(siren) == 0

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

# Matches a French street address: number + street type + name + postal code + city.
# Works on normalized text (no accents, lowercase).
# City capture stops at " - " separator (used between legal mentions in OCR text).
ADDRESS_RE = re.compile(
    r"\d+\s*,?\s*"
    r"(?:rue|avenue|av\.?\s|boulevard|bd\.?\s|place|impasse|allee|chemin|route|quai|square|cours|voie)\b"
    r"(?:(?!\s+-\s).){3,60}?"
    r"\b\d{5}\b"
    r"\s+(?:[\w](?:(?!\s+-\s)[\w\s]){0,25})",
    re.IGNORECASE,
)


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
            if not validate_siren(siren):
                results.append(
                    CheckResult(
                        check_name="advertiser",
                        severity=Severity.WARNING,
                        message=f"RCS détecté avec SIREN invalide : {city} {siren}.",
                        details={"ville": city, "siren": siren},
                    )
                )
            else:
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
    addr_match = ADDRESS_RE.search(norm)
    if addr_match:
        address = addr_match.group(0).strip().rstrip(" -,")
        address = re.sub(r"\s+france\s*$", "", address, flags=re.IGNORECASE).rstrip(" ,")
        results.append(
            CheckResult(
                check_name="advertiser",
                severity=Severity.INFO,
                message=f"Adresse détectée : « {address} »",
            )
        )
    elif POSTAL_CODE_RE.search(norm):
        # Fallback: code postal trouvé mais motif d'adresse non reconnu
        postal_match = POSTAL_CODE_RE.search(norm)
        start = max(0, postal_match.start() - 60)
        end = min(len(norm), postal_match.end() + 30)
        snippet = norm[start:end].strip()
        results.append(
            CheckResult(
                check_name="advertiser",
                severity=Severity.INFO,
                message=f"Adresse détectée : « {snippet} »",
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


__all__ = ["check_advertiser", "RCS_RE", "validate_siren"]
