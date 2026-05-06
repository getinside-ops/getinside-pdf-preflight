"""Font embedding verification."""

from __future__ import annotations

from preflight.checks import CheckResult, Severity
from preflight.document import Document
from preflight.snapshot import DocumentSnapshot

_STANDARD_FONTS = {
    "Arial",
    "Helvetica",
    "Times",
    "Courier",
    "Symbol",
    "ZapfDingbats",
    "Verdana",
    "Tahoma",
    "Georgia",
    "Trebuchet",
}


def check_font_embedding(document: Document, snapshot: DocumentSnapshot) -> list[CheckResult]:
    """Check that all fonts in PDF are embedded."""
    results: list[CheckResult] = []

    if document.kind != "pdf":
        return results

    try:
        for page in document.pages:
            for font_info in snapshot.page_fonts.get(page.index, []):
                # get_fonts(full=True) → (xref, ext, type, basefont, name, encoding, referencer)
                font_name = font_info[3] if len(font_info) > 3 else ""  # basefont

                if not font_name:
                    continue

                # Subset fonts have a 6-uppercase-letter prefix followed by '+'
                is_subset = (
                    len(font_name) > 7
                    and font_name[:6].isupper()
                    and font_name[6] == "+"
                )

                # Strip subset prefix and variant suffix to get the base family name
                base_name = font_name.split("+")[-1].split("-")[0] if "+" in font_name else font_name

                if base_name in _STANDARD_FONTS and not is_subset:
                    results.append(
                        CheckResult(
                            check_name="font_embedding",
                            severity=Severity.WARNING,
                            message=f"Police '{font_name}' potentiellement non embarquée",
                            details={"font": font_name, "page": page.index + 1},
                            page=page.index,
                        )
                    )
    except Exception as exc:
        results.append(
            CheckResult(
                check_name="font_embedding",
                severity=Severity.WARNING,
                message=f"Impossible de vérifier les polices: {exc}",
            )
        )

    return results


__all__ = ["check_font_embedding"]