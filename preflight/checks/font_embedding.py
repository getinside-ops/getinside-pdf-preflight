"""Font embedding verification."""

from typing import List

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


def check_font_embedding(document: Document, snapshot: DocumentSnapshot) -> List[CheckResult]:
    """Check that all fonts in PDF are embedded."""
    results: List[CheckResult] = []

    if document.kind != "pdf":
        return results

    try:
        for page_num in range(len(document.pages)):
            for font_info in snapshot.page_fonts.get(page_num, []):
                # font_info[0] = path/subset, font_info[1] = name
                font_name = font_info[1] if len(font_info) > 1 else ""
                font_subset = font_info[0] if len(font_info) > 0 else ""

                if not font_name:
                    continue

                # Check if it's a subset (starts with 6 uppercase letters)
                is_subset = len(font_name) > 6 and font_name[:6].isupper() and font_name[6] == "+"

                # Check for unembedded standard fonts
                base_name = font_name.split("+")[-1].split("-")[0] if "+" in font_name else font_name

                if base_name in _STANDARD_FONTS and not is_subset:
                    results.append(
                        CheckResult(
                            check_name="font_embedding",
                            severity=Severity.WARNING,
                            message=f"Police '{font_name}' potentiellement non embarquée",
                            details={"font": font_name, "page": page_num + 1},
                            page=page_num,
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