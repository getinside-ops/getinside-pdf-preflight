"""Spot colors detection."""

from typing import List

from preflight.checks import CheckResult, Severity
from preflight.document import Document


def check_spot_colors(document: Document) -> List[CheckResult]:
    """Detect spot colors not converted to CMYK."""
    results: List[CheckResult] = []

    if document.kind != "pdf":
        return results

    try:
        fitz_doc = document._fitz_doc
        for page_num, page in enumerate(fitz_doc):
            for img_index, img in enumerate(page.get_images(full=True)):
                # img[2] = colorspace: 1=gray, 3=rgb, 4=cmyk
                colorspace = img[2] if len(img) > 2 else None

                # DeviceN (6) or Separation (2) indicates spot colors
                if colorspace in (2, 6):
                    results.append(
                        CheckResult(
                            check_name="spot_colors",
                            severity=Severity.ERROR,
                            message=f"Couleur spot détectée (type {colorspace})",
                            details={"page": page_num + 1, "image_index": img_index},
                            page=page_num,
                        )
                    )
    except Exception as exc:
        results.append(
            CheckResult(
                check_name="spot_colors",
                severity=Severity.WARNING,
                message=f"Impossible de vérifier les couleurs: {exc}",
            )
        )

    return results


__all__ = ["check_spot_colors"]