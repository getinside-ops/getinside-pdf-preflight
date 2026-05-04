"""Industry-specific legal mention check."""

from __future__ import annotations

from preflight.checks import CheckResult, Severity
from preflight.industries import IndustryRule, get_industry
from preflight.text_normalize import fuzzy_contains, normalize


def check_industry(all_text: str, industry: str) -> list[CheckResult]:
    rule: IndustryRule = get_industry(industry)
    if rule.name == "Général":
        return [
            CheckResult(
                check_name="industry",
                severity=Severity.INFO,
                message="Industrie « Général » — aucune mention sectorielle obligatoire.",
            )
        ]

    results: list[CheckResult] = []

    for phrase in rule.required_phrases:
        if fuzzy_contains(all_text, phrase, threshold=85):
            results.append(
                CheckResult(
                    check_name="industry",
                    severity=Severity.INFO,
                    message=f"[{rule.name}] Phrase obligatoire trouvée : « {phrase} »",
                )
            )
        else:
            results.append(
                CheckResult(
                    check_name="industry",
                    severity=Severity.ERROR,
                    message=f"[{rule.name}] Phrase obligatoire manquante : « {phrase} »",
                    details={"industry": rule.name, "expected": phrase},
                )
            )

    for group in rule.any_of_groups:
        match = next((p for p in group if fuzzy_contains(all_text, p, threshold=85)), None)
        if match:
            results.append(
                CheckResult(
                    check_name="industry",
                    severity=Severity.INFO,
                    message=f"[{rule.name}] Mention au choix trouvée : « {match} »",
                )
            )
        else:
            results.append(
                CheckResult(
                    check_name="industry",
                    severity=Severity.ERROR,
                    message=(
                        f"[{rule.name}] Aucune des mentions équivalentes trouvée. "
                        f"Choisir au moins une parmi : « {' »  ou  « '.join(group)} »"
                    ),
                    details={"industry": rule.name, "any_of": list(group)},
                )
            )

    norm_text = normalize(all_text)
    for label, pattern in rule.regex_requirements:
        if pattern.search(norm_text):
            results.append(
                CheckResult(
                    check_name="industry",
                    severity=Severity.INFO,
                    message=f"[{rule.name}] {label} : motif détecté.",
                )
            )
        else:
            results.append(
                CheckResult(
                    check_name="industry",
                    severity=Severity.ERROR,
                    message=f"[{rule.name}] {label} : aucune donnée détectée.",
                    details={"pattern": pattern.pattern},
                )
            )

    return results


__all__ = ["check_industry"]
