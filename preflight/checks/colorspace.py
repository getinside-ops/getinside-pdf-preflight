"""Color space check.

For PDFs, walks every embedded image to detect RGB content. For images,
reads the PIL mode. The TAC/ICC advisory is always emitted as INFO.
"""

from __future__ import annotations

from pathlib import Path

from preflight.checks import CheckResult, Severity
from preflight.document import Document, ImagePage

TAC_ICC_ADVISORY = (
    "Vérifiez manuellement le taux d'encrage (≤ 300 %) et le profil ICC "
    "(Coated FOGRA39 recommandé pour l'impression européenne)."
)


def check_colorspace(document: Document) -> list[CheckResult]:
    results: list[CheckResult] = []

    if document.kind == "pdf":
        all_spaces: set[str] = set()
        for page in document.pages:
            spaces = page.color_spaces()
            all_spaces.update(spaces)
            if "RGB" in spaces:
                results.append(
                    CheckResult(
                        check_name="colorspace",
                        severity=Severity.ERROR,
                        message=(
                            f"page {page.index + 1}: contient des images en RGB. "
                            f"Convertissez en CMYK avant impression."
                        ),
                        page=page.index,
                        details={"spaces": sorted(spaces)},
                    )
                )
        if all_spaces:
            results.append(
                CheckResult(
                    check_name="colorspace",
                    severity=Severity.INFO,
                    message=(
                        f"Espaces de couleur détectés dans le PDF : {', '.join(sorted(all_spaces))}."
                    ),
                    details={"spaces": sorted(all_spaces)},
                )
            )
    else:
        for page in document.pages:
            assert isinstance(page, ImagePage)
            spaces = page.color_spaces()
            file_format = page.file_format()
            if file_format == "png":
                results.append(
                    CheckResult(
                        check_name="colorspace",
                        severity=Severity.WARNING,
                        message=(
                            f"page {page.index + 1}: PNG ne supporte pas le CMYK nativement. "
                            f"Pour l'impression, fournissez plutôt un PDF ou un TIFF CMYK."
                        ),
                        page=page.index,
                        details={"format": "png", "mode": next(iter(spaces), "")},
                    )
                )
            elif file_format == "jpeg":
                if "CMYK" not in spaces:
                    results.append(
                        CheckResult(
                            check_name="colorspace",
                            severity=Severity.ERROR,
                            message=(
                                f"page {page.index + 1}: JPEG en {next(iter(spaces), 'inconnu')} "
                                f"alors que CMYK est attendu pour l'impression."
                            ),
                            page=page.index,
                            details={"spaces": sorted(spaces)},
                        )
                    )
                else:
                    results.append(
                        CheckResult(
                            check_name="colorspace",
                            severity=Severity.INFO,
                            message=f"page {page.index + 1}: JPEG en CMYK.",
                            page=page.index,
                        )
                    )

    results.append(
        CheckResult(
            check_name="colorspace",
            severity=Severity.INFO,
            message=TAC_ICC_ADVISORY,
        )
    )
    return results


__all__ = ["check_colorspace", "TAC_ICC_ADVISORY"]
