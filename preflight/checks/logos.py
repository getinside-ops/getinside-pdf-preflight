"""Logo presence check via perceptual-hash matching.

Notes:
* Cartouche Info-tri is required on every printed asset.
* The Getinside logo is required only when the user prints the asset
  themselves ("Imprimé par la marque").
* When the logo library is empty, all checks fall back to INFO-level
  manual-verification reminders. This keeps the tool honest.
"""

from __future__ import annotations

from typing import Literal

from preflight.checks import CheckResult, Severity
from preflight.document import Document
from preflight.logos import LogoLibrary, DEFAULT_THRESHOLD, SOFT_THRESHOLD
from preflight.snapshot import DocumentSnapshot

PrintMethod = Literal["Imprimé par getinside", "Imprimé par la marque"]

REQUIRED_CATEGORIES = {"cartouche_info_tri": "Cartouche Info-tri"}
SELF_PRINT_CATEGORIES = {"getinside": "Logo getinside"}


def check_logos(
    document: Document,
    library: LogoLibrary,
    print_method: PrintMethod,
    snapshot: DocumentSnapshot,
    *,
    threshold: int = DEFAULT_THRESHOLD,
) -> list[CheckResult]:
    if library.is_empty:
        return [
            CheckResult(
                check_name="logos",
                severity=Severity.INFO,
                message=(
                    "Bibliothèque de logos non configurée — vérification manuelle requise pour "
                    "le Cartouche Info-tri (≥ 8 mm) et le logo getinside."
                ),
            )
        ]

    expected: dict[str, str] = dict(REQUIRED_CATEGORIES)
    if print_method == "Imprimé par la marque":
        expected.update(SELF_PRINT_CATEGORIES)

    # Aggregate matches across all pages: a logo on either side counts.
    # Render at 300 DPI so small logos (8-15 mm) have enough pixels for crops.
    aggregated: dict[str, int] = {}  # category -> best (lowest) distance
    for page in document.pages:
        rendered = snapshot.page_renders[page.index]
        per_cat = library.all_distances(rendered)
        for cat, match in per_cat.items():
            if cat not in aggregated or match.distance < aggregated[cat]:
                aggregated[cat] = match.distance

    results: list[CheckResult] = []
    for cat, label in expected.items():
        if cat not in library.categories:
            results.append(
                CheckResult(
                    check_name="logos",
                    severity=Severity.INFO,
                    message=(
                        f"{label}: aucune référence dans la bibliothèque — vérification manuelle requise."
                    ),
                    details={"category": cat},
                )
            )
            continue
        distance = aggregated.get(cat)
        if distance is None or distance > SOFT_THRESHOLD:
            results.append(
                CheckResult(
                    check_name="logos",
                    severity=Severity.ERROR,
                    message=(
                        f"{label} introuvable sur le document "
                        f"(distance phash {distance if distance is not None else '∞'}, "
                        f"seuil ≤ {threshold})."
                    ),
                    details={"category": cat, "best_distance": distance, "threshold": threshold},
                )
            )
        elif distance > threshold:
            results.append(
                CheckResult(
                    check_name="logos",
                    severity=Severity.WARNING,
                    message=(
                        f"{label}: correspondance probable mais incertaine "
                        f"(distance {distance}, seuil strict ≤ {threshold}). "
                        f"Vérifiez visuellement."
                    ),
                    details={"category": cat, "distance": distance},
                )
            )
        else:
            results.append(
                CheckResult(
                    check_name="logos",
                    severity=Severity.INFO,
                    message=(
                        f"{label}: correspondance phash à distance {distance} (seuil ≤ {threshold})."
                    ),
                    details={"category": cat, "distance": distance},
                )
            )

    # 8mm size advisory — phash doesn't localize, so we surface it as INFO.
    if "cartouche_info_tri" in expected:
        results.append(
            CheckResult(
                check_name="logos",
                severity=Severity.INFO,
                message=(
                    "Vérifiez visuellement que le Cartouche Info-tri mesure au moins 8 mm "
                    "sur son petit côté (la détection phash ne mesure pas la taille à l'écran)."
                ),
            )
        )
    return results


__all__ = ["check_logos", "PrintMethod"]
