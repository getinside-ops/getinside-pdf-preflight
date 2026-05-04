"""Printer mention check."""

from __future__ import annotations

from typing import Literal

from preflight.checks import CheckResult, Severity
from preflight.text_normalize import fuzzy_contains

PrintMethod = Literal["Imprimé par getinside", "Imprimé par la marque"]

GETINSIDE_PRINTER_MENTION = (
    "Imprimé sur papier FSC par un imprimeur certifié Imprim'vert avec getinside"
)


def check_printer(all_text: str, print_method: PrintMethod) -> list[CheckResult]:
    if print_method != "Imprimé par la marque":
        if fuzzy_contains(all_text, GETINSIDE_PRINTER_MENTION, threshold=85):
            return [
                CheckResult(
                    check_name="printer",
                    severity=Severity.INFO,
                    message="Mention imprimeur getinside détectée.",
                )
            ]
        return [
            CheckResult(
                check_name="printer",
                severity=Severity.ERROR,
                message=(
                    f"Mention imprimeur manquante. Phrase exacte attendue : "
                    f"« {GETINSIDE_PRINTER_MENTION} »."
                ),
                details={"expected": GETINSIDE_PRINTER_MENTION},
            )
        ]
    return [
        CheckResult(
            check_name="printer",
            severity=Severity.INFO,
            message=(
                "Impression assurée par l'annonceur — assurez-vous que le logo getinside "
                "est bien présent et que vous respectez les obligations d'impression."
            ),
        )
    ]


__all__ = ["check_printer", "GETINSIDE_PRINTER_MENTION", "PrintMethod"]
