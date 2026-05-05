"""Check embedded image resolution in PDFs."""

from __future__ import annotations

from preflight.checks import CheckResult, Severity
from preflight.document import Document


def check_image_resolution(document: Document) -> list[CheckResult]:
    results: list[CheckResult] = []

    for page in document.pages:
        if page.source != "pdf":
            continue

        page_obj = page._page
        images = page_obj.get_images()

        if not images:
            continue

        dpi_list: list[float] = []
        page_width_pt = page_obj.rect.width

        for img in images:
            img_width = img[2]
            dpi = (img_width / page_width_pt) * 72
            dpi_list.append(dpi)

        if not dpi_list:
            continue

        min_dpi = min(dpi_list)
        avg_dpi = sum(dpi_list) / len(dpi_list)

        if min_dpi < 50:
            severity = Severity.ERROR
            msg = (
                f"Page {page.index + 1}: résolution image trop basse "
                f"({min_dpi:.0f} DPI)"
            )
        elif min_dpi < 100:
            severity = Severity.WARNING
            msg = f"Page {page.index + 1}: résolution image limite ({min_dpi:.0f} DPI)"
        else:
            severity = Severity.INFO
            msg = f"Page {page.index + 1}: résolution image OK ({min_dpi:.0f} DPI)"

        results.append(
            CheckResult(
                check_name="image_resolution",
                severity=severity,
                message=msg,
                details={
                    "count": len(dpi_list),
                    "min_dpi": round(min_dpi, 1),
                    "avg_dpi": round(avg_dpi, 1),
                },
                page=page.index,
            )
        )

    return results