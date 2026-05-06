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
        image_infos = page_obj.get_image_info(hashes=False)

        if not image_infos:
            continue

        dpi_list: list[tuple[float, tuple[float, float, float, float] | None]] = []

        for info in image_infos:
            img_width_px = info.get("width", 0)
            bbox = info.get("bbox")
            if bbox is not None:
                placed_w_pt = bbox[2] - bbox[0]  # x1 - x0
                dpi = (img_width_px / placed_w_pt) * 72.0 if placed_w_pt > 0 else 0.0
                bbox_tuple: tuple[float, float, float, float] | None = (
                    float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                )
            else:
                page_width_pt = page_obj.rect.width
                dpi = (img_width_px / page_width_pt) * 72.0 if page_width_pt > 0 else 0.0
                bbox_tuple = None
            dpi_list.append((dpi, bbox_tuple))

        if not dpi_list:
            continue

        min_dpi = min(d for d, _ in dpi_list)
        avg_dpi = sum(d for d, _ in dpi_list) / len(dpi_list)
        worst_bbox = min(dpi_list, key=lambda x: x[0])[1]

        if min_dpi < 50:
            severity = Severity.ERROR
            msg = (
                f"Page {page.index + 1}: résolution image trop basse "
                f"({min_dpi:.0f} DPI)"
            )
            result_bbox = worst_bbox
        elif min_dpi < 100:
            severity = Severity.WARNING
            msg = f"Page {page.index + 1}: résolution image limite ({min_dpi:.0f} DPI)"
            result_bbox = worst_bbox
        else:
            severity = Severity.INFO
            msg = f"Page {page.index + 1}: résolution image OK ({min_dpi:.0f} DPI)"
            result_bbox = None

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
                bbox=result_bbox,
            )
        )

    return results


__all__ = ["check_image_resolution"]
