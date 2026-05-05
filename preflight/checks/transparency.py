"""Detect transparency/alpha channels in PDF."""

from __future__ import annotations

from preflight.checks import CheckResult, Severity
from preflight.document import Document


def check_transparency(document: Document) -> list[CheckResult]:
    results: list[CheckResult] = []

    for page in document.pages:
        if page.source != "pdf":
            continue

        page_obj = page._page
        images = page_obj.get_images()

        has_transparency = False
        alpha_count = 0

        for img in images:
            if len(img) >= 7:
                n = img[6]
                try:
                    n = int(n)
                except (ValueError, TypeError):
                    continue
                if n == 4 or n > 4:
                    has_transparency = True
                    alpha_count += 1

        if has_transparency:
            results.append(
                CheckResult(
                    check_name="transparency",
                    severity=Severity.ERROR,
                    message=(
                        f"Page {page.index + 1}: transparence détectée "
                        f"({alpha_count} images avec alpha)"
                    ),
                    details={"count": alpha_count},
                    page=page.index,
                )
            )
        else:
            results.append(
                CheckResult(
                    check_name="transparency",
                    severity=Severity.INFO,
                    message=f"Page {page.index + 1}: pas de transparence",
                    details={"count": 0},
                    page=page.index,
                )
            )

    return results