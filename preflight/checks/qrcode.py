"""QR code check.

Document-level: a recto-verso flyer typically only carries the QR on one
side, so we collect detections across all pages and only fail if no
compliant QR is found anywhere. Per-detection size and URL checks still
apply individually.

The QR must redirect through gtinsi.de/ — this is mandatory and hardcoded.
"""

from __future__ import annotations

from preflight.checks import CheckResult, Severity
from preflight.document import Document
from preflight.qr import detect_qr_codes
from preflight.snapshot import DocumentSnapshot, SNAPSHOT_RENDER_DPI
from preflight.text_normalize import normalize

MIN_QR_SIZE_MM = 25.0
BASE_URL = "gtinsi.de/"


def check_qr(document: Document, snapshot: DocumentSnapshot) -> list[CheckResult]:
    results: list[CheckResult] = []
    target = normalize(BASE_URL)

    detections_per_page: list[tuple[int, list]] = []
    for page in document.pages:
        image = snapshot.page_renders[page.index]
        dpi = float(SNAPSHOT_RENDER_DPI) if page.source == "pdf" else (page.dpi() or 72.0)
        detections_per_page.append((page.index, detect_qr_codes(image, dpi=dpi)))

    total = sum(len(dets) for _, dets in detections_per_page)
    if total == 0:
        results.append(
            CheckResult(
                check_name="qrcode",
                severity=Severity.ERROR,
                message="Aucun QR code détecté sur le document.",
            )
        )
        return results

    has_compliant_url = False
    for page_index, dets in detections_per_page:
        page_label = f"page {page_index + 1}"
        for det in dets:
            results.append(
                CheckResult(
                    check_name="qrcode",
                    severity=Severity.INFO,
                    message=f"{page_label}: QR code détecté → {det.data}",
                    page=page_index,
                    details={"data": det.data, "size_mm": det.bbox_mm},
                )
            )
            if det.short_side_mm is not None and det.short_side_mm < MIN_QR_SIZE_MM:
                results.append(
                    CheckResult(
                        check_name="qrcode",
                        severity=Severity.ERROR,
                        message=(
                            f"{page_label}: QR code trop petit "
                            f"({det.short_side_mm:.1f} mm de côté, minimum {MIN_QR_SIZE_MM:.0f} mm)."
                        ),
                        page=page_index,
                        details={"short_side_mm": det.short_side_mm},
                    )
                )
            if not target or target in normalize(det.data):
                has_compliant_url = True

    if not has_compliant_url:
        detected = [det.data for _, dets in detections_per_page for det in dets]
        results.append(
            CheckResult(
                check_name="qrcode",
                severity=Severity.ERROR,
                message=(
                    f"Aucun QR code ne pointe vers {BASE_URL} (obligatoire)."
                ),
                details={"detected": detected, "expected_contains": BASE_URL},
            )
        )

    return results


__all__ = ["BASE_URL", "check_qr", "MIN_QR_SIZE_MM"]
