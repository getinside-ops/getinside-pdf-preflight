"""Dimension and DPI check."""

from __future__ import annotations

from preflight.checks import CheckResult, Severity
from preflight.document import Document
from preflight.formats import FormatSpec


def check_dimensions(document: Document, format_spec: FormatSpec) -> list[CheckResult]:
    results: list[CheckResult] = []

    for page in document.pages:
        page_label = f"page {page.index + 1}"
        box = page.dimensions_mm()
        ok, kind = format_spec.matches_dimensions(box.width, box.height)
        details = {
            "found_mm": (round(box.width, 2), round(box.height, 2)),
            "expected_final_mm": (format_spec.final_w_mm, format_spec.final_h_mm),
            "expected_bleed_mm": (format_spec.bleed_w_mm, format_spec.bleed_h_mm),
            "tolerance_mm": format_spec.tolerance_mm,
        }
        if ok:
            results.append(
                CheckResult(
                    check_name="dimensions",
                    severity=Severity.INFO,
                    message=(
                        f"{page_label}: dimensions {kind} ({box.width:.1f}×{box.height:.1f} mm) "
                        f"conformes au format {format_spec.name}."
                    ),
                    details={**details, "kind": kind},
                    page=page.index,
                )
            )
        else:
            results.append(
                CheckResult(
                    check_name="dimensions",
                    severity=Severity.ERROR,
                    message=(
                        f"{page_label}: dimensions {box.width:.1f}×{box.height:.1f} mm ne correspondent ni "
                        f"au format {format_spec.name} final ({format_spec.final_w_mm}×{format_spec.final_h_mm} mm) "
                        f"ni avec fond perdu ({format_spec.bleed_w_mm}×{format_spec.bleed_h_mm} mm)."
                    ),
                    details=details,
                    page=page.index,
                )
            )

        if page.source == "pdf":
            results.extend(_pdf_box_consistency(page, format_spec))
        else:
            results.extend(_image_dpi_check(page, format_spec))

    return results


def _pdf_box_consistency(page, format_spec: FormatSpec) -> list[CheckResult]:
    """For PDFs, check whether bleed appears to be set up via TrimBox."""
    trim = page.trim_box_mm()
    media = page.media_box_mm()
    if trim is None and media is not None:
        # No explicit TrimBox → printer cannot tell where the trim is.
        return [
            CheckResult(
                check_name="dimensions",
                severity=Severity.WARNING,
                message=(
                    f"page {page.index + 1}: aucun TrimBox détecté. Le PDF doit définir un TrimBox "
                    f"correspondant à la taille finale, le MediaBox couvrant la taille avec fond perdu."
                ),
                details={"media_box_mm": (round(media.width, 2), round(media.height, 2))},
                page=page.index,
            )
        ]
    if trim is not None and media is not None:
        results: list[CheckResult] = []
        expected_bleed_w = trim.width + 2 * format_spec.bleed_mm
        expected_bleed_h = trim.height + 2 * format_spec.bleed_mm
        if (
            abs(media.width - expected_bleed_w) > format_spec.tolerance_mm
            or abs(media.height - expected_bleed_h) > format_spec.tolerance_mm
        ):
            results.append(
                CheckResult(
                    check_name="dimensions",
                    severity=Severity.WARNING,
                    message=(
                        f"page {page.index + 1}: l'écart MediaBox/TrimBox ne correspond pas au fond perdu "
                        f"attendu de {format_spec.bleed_mm} mm par côté. "
                        f"(Si le PDF inclut des traits de coupe, c'est normal — vérifiez que le TrimBox "
                        f"correspond bien au format final.)"
                    ),
                    details={
                        "trim_box_mm": (round(trim.width, 2), round(trim.height, 2)),
                        "media_box_mm": (round(media.width, 2), round(media.height, 2)),
                    },
                    page=page.index,
                )
            )

        # Trim marks
        if page.has_trim_marks():
            results.append(
                CheckResult(
                    check_name="dimensions",
                    severity=Severity.INFO,
                    message=f"page {page.index + 1}: traits de coupe détectés.",
                    page=page.index,
                )
            )

        # Safe zone
        violations = page.safe_zone_violations_mm(format_spec.safe_zone_mm)
        if violations:
            worst = min(violations, key=lambda v: v["min_dist_mm"])
            results.append(
                CheckResult(
                    check_name="dimensions",
                    severity=Severity.WARNING,
                    message=(
                        f"page {page.index + 1}: contenu dans la zone tranquille "
                        f"(< {format_spec.safe_zone_mm} mm du bord final). "
                        f"Exemple : « {worst['text']} » à {worst['min_dist_mm']} mm."
                    ),
                    details={
                        "violations_count": len(violations),
                        "min_dist_mm": worst["min_dist_mm"],
                    },
                    page=page.index,
                    bbox=worst.get("bbox"),
                )
            )
        else:
            results.append(
                CheckResult(
                    check_name="dimensions",
                    severity=Severity.INFO,
                    message=(
                        f"page {page.index + 1}: zone tranquille respectée "
                        f"(≥ {format_spec.safe_zone_mm} mm depuis le bord final)."
                    ),
                    page=page.index,
                )
            )

        return results
    return []


def _image_dpi_check(page, format_spec: FormatSpec) -> list[CheckResult]:
    dpi = page.dpi()
    if dpi is None:
        return [
            CheckResult(
                check_name="dimensions",
                severity=Severity.WARNING,
                message=(
                    f"page {page.index + 1}: aucune information DPI dans l'image. "
                    f"Impossible de vérifier la résolution; vérifiez manuellement (≥{format_spec.min_dpi} DPI requis)."
                ),
                page=page.index,
            )
        ]
    if dpi < format_spec.min_dpi:
        return [
            CheckResult(
                check_name="dimensions",
                severity=Severity.ERROR,
                message=(
                    f"page {page.index + 1}: résolution {dpi:.0f} DPI insuffisante "
                    f"(minimum {format_spec.min_dpi} DPI)."
                ),
                details={"dpi": dpi, "min_dpi": format_spec.min_dpi},
                page=page.index,
            )
        ]
    return [
        CheckResult(
            check_name="dimensions",
            severity=Severity.INFO,
            message=f"page {page.index + 1}: résolution {dpi:.0f} DPI.",
            page=page.index,
        )
    ]


__all__ = ["check_dimensions"]
