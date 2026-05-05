"""Check text contrast for readability (WCAG)."""

from __future__ import annotations

from preflight.checks import CheckResult, Severity
from preflight.document import Document


def _luminance(r: int, g: int, b: int) -> float:
    def adj(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * adj(r) + 0.7152 * adj(g) + 0.0722 * adj(b)


def _contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    l1 = _luminance(*fg) + 0.05
    l2 = _luminance(*bg) + 0.05
    return max(l1, l2) / min(l1, l2)


def check_contrast(document: Document) -> list[CheckResult]:
    results: list[CheckResult] = []

    for page in document.pages:
        if page.source != "pdf":
            continue

        page_obj = page._page
        text_dict = page_obj.get_text("dict")

        low_contrast_count = 0
        worst_ratio = 21.0

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    color = span.get("color", 0)
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF

                    if r == g == b == 0:
                        ratio = 21.0
                    else:
                        ratio = _contrast_ratio((r, g, b), (255, 255, 255))

                    if ratio < 4.5:
                        low_contrast_count += 1
                    worst_ratio = min(worst_ratio, ratio)

        if low_contrast_count > 0:
            if worst_ratio < 3.0:
                severity = Severity.ERROR
            else:
                severity = Severity.WARNING
            msg = (
                f"Page {page.index + 1}: {low_contrast_count} zones de texte "
                f"à faible contraste (pire: {worst_ratio:.1f}:1)"
            )
        else:
            severity = Severity.INFO
            msg = f"Page {page.index + 1}: contraste texte OK"

        results.append(
            CheckResult(
                check_name="contrast",
                severity=severity,
                message=msg,
                details={
                    "low_contrast_count": low_contrast_count,
                    "worst_ratio": round(worst_ratio, 2),
                },
                page=page.index,
            )
        )

    return results