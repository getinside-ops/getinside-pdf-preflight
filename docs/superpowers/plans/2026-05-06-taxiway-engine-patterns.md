# Taxiway Engine Patterns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port three engine architecture patterns from Taxiway (Swift PDF preflight tool) into this codebase: severity overrides on `CheckContext`, bounding boxes in `CheckResult`, and a `DocumentSnapshot` pre-parse cache.

**Architecture:** Three independent features, each building on the previous. Feature 1 adds a `severity_overrides` dict to `CheckContext` and applies it post-run in the pipeline. Feature 2 adds a `bbox` field to `CheckResult` and populates it in checks that have geometric context (dimensions safe-zone violations, low-res image locations). Feature 3 introduces a `DocumentSnapshot` dataclass built once per pipeline run that caches expensive per-page operations (renders, image info, font lists), eliminating redundant re-computation across checks.

**Tech Stack:** Python 3.13, PyMuPDF (`fitz`), PIL/Pillow, pytest — all already in the project.

---

## File Map

| File | Role |
|------|------|
| `preflight/checks/__init__.py` | Add `bbox` field to `CheckResult` |
| `preflight/document.py` | Update `safe_zone_violations_mm()` to return bbox |
| `preflight/snapshot.py` | **New** — `DocumentSnapshot` dataclass + `build()` |
| `preflight/pipeline.py` | Add `severity_overrides`, build + pass snapshot, apply overrides |
| `preflight/checks/dimensions.py` | Store bbox from safe-zone violations |
| `preflight/checks/image_resolution.py` | Switch to `get_image_info()`, store bbox, use snapshot |
| `preflight/checks/logos.py` | Accept + use `snapshot.page_renders` |
| `preflight/checks/qrcode.py` | Accept + use `snapshot.page_renders` |
| `preflight/checks/font_embedding.py` | Accept + use `snapshot.page_fonts` |
| `tests/test_checks_bbox.py` | **New** — bbox population tests |
| `tests/test_snapshot.py` | **New** — snapshot build + integration tests |
| `tests/test_pipeline_integration.py` | Add severity-override test |
| `tests/test_checks_visual.py` | Update logos/qr call sites |
| `tests/test_logos.py` | Update logos call sites |

---

## Task 1: Severity Overrides on CheckContext

**Files:**
- Modify: `preflight/pipeline.py`
- Modify: `tests/test_pipeline_integration.py`

### Background

`CheckContext` currently holds `format_spec`, `industry`, and `print_method`. There is no way to soften or suppress a check without editing its source. Adding `severity_overrides: dict[str, Severity]` allows the caller to say "treat `colorspace` warnings as INFO" without touching business logic — the same approach Taxiway uses in its profile system.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_pipeline_integration.py`:

```python
from preflight.checks import Severity
from preflight.pipeline import CheckContext, run_all_checks
from preflight.formats import get_format


def test_severity_override_downgrades_matching_check(pdf_a5_single):
    from preflight.document import Document
    doc = Document.from_upload([pdf_a5_single])
    # colorspace check normally produces at least one result (the TAC/ICC advisory INFO)
    # and an ERROR for missing CMYK on plain text PDFs.
    # Override colorspace to INFO so ERRORs from it become INFO.
    ctx = CheckContext(
        format_spec=get_format("A5"),
        severity_overrides={"colorspace": Severity.INFO},
    )
    results = run_all_checks(doc, ctx)
    colorspace_results = [r for r in results if r.check_name == "colorspace"]
    assert colorspace_results, "colorspace check must produce results"
    assert all(r.severity is Severity.INFO for r in colorspace_results), (
        "All colorspace results should be downgraded to INFO"
    )


def test_severity_override_does_not_affect_other_checks(pdf_a5_single):
    from preflight.document import Document
    doc = Document.from_upload([pdf_a5_single])
    ctx = CheckContext(
        format_spec=get_format("A5"),
        severity_overrides={"colorspace": Severity.INFO},
    )
    results = run_all_checks(doc, ctx)
    non_colorspace = [r for r in results if r.check_name != "colorspace"]
    # dimensions check should still have INFO/WARNING/ERROR unaffected
    assert non_colorspace, "other checks must still run"


def test_severity_override_empty_dict_is_noop(pdf_a5_single):
    from preflight.document import Document
    doc = Document.from_upload([pdf_a5_single])
    ctx_no_override = CheckContext(format_spec=get_format("A5"))
    ctx_empty = CheckContext(format_spec=get_format("A5"), severity_overrides={})
    results_no = run_all_checks(doc, ctx_no_override)
    results_empty = run_all_checks(doc, ctx_empty)
    assert [(r.check_name, r.severity) for r in results_no] == [
        (r.check_name, r.severity) for r in results_empty
    ]
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
.venv/bin/pytest tests/test_pipeline_integration.py::test_severity_override_downgrades_matching_check -v
```

Expected: `FAILED` — `CheckContext.__init__() got an unexpected keyword argument 'severity_overrides'`

- [ ] **Step 3: Add `severity_overrides` to `CheckContext` and apply it in the pipeline**

In `preflight/pipeline.py`, replace the `CheckContext` dataclass and add a helper:

```python
from __future__ import annotations

from dataclasses import dataclass, field
# ... existing imports ...


@dataclass
class CheckContext:
    format_spec: FormatSpec
    industry: str = ""
    print_method: PrintMethod = "Imprimé par getinside"
    severity_overrides: dict[str, Severity] = field(default_factory=dict)


def _apply_severity_overrides(
    results: list[CheckResult], overrides: dict[str, Severity]
) -> list[CheckResult]:
    if not overrides:
        return results
    return [
        CheckResult(
            check_name=r.check_name,
            severity=overrides[r.check_name] if r.check_name in overrides else r.severity,
            message=r.message,
            details=r.details,
            page=r.page,
        )
        for r in results
    ]
```

At the end of `run_all_checks`, replace `return results` with:

```python
    return _apply_severity_overrides(results, context.severity_overrides)
```

At the end of `run_all_checks_with_extraction`, replace `return results, extraction_info` with:

```python
    results = _apply_severity_overrides(results, context.severity_overrides)
    return results, extraction_info
```

Also add `_apply_severity_overrides` to `__all__`.

- [ ] **Step 4: Run all three new tests**

```bash
.venv/bin/pytest tests/test_pipeline_integration.py -k "severity_override" -v
```

Expected: 3 × `PASSED`

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
.venv/bin/pytest -q
```

Expected: all tests pass (the `severity_overrides` field defaults to `{}` so existing tests are unaffected).

- [ ] **Step 6: Commit**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
rtk git add preflight/pipeline.py tests/test_pipeline_integration.py
rtk git commit -m "feat: add severity_overrides to CheckContext for per-check severity tuning"
```

---

## Task 2: Bounding Boxes in CheckResult

**Files:**
- Modify: `preflight/checks/__init__.py`
- Modify: `preflight/document.py`
- Modify: `preflight/checks/dimensions.py`
- Modify: `preflight/checks/image_resolution.py`
- Create: `tests/test_checks_bbox.py`

### Background

`CheckResult` currently carries a `page` index but no coordinate info. Taxiway attaches per-element bounding boxes (`AffectedItem` with `AnnotationBounds`) to every result that has geometric context. Adding a `bbox: tuple[float, float, float, float] | None` field (x0, y0, x1, y1 in PDF page points) to `CheckResult` enables the UI to draw overlays on page thumbnails.

Two checks have bbox data today:
- **dimensions**: `safe_zone_violations_mm()` already computes `block_rect` (a `fitz.Rect`) but discards it.
- **image_resolution**: currently uses `get_images()` which has no placement data; switching to `get_image_info()` gives a `bbox` per image.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_checks_bbox.py`:

```python
"""Tests that CheckResult.bbox is populated where geometric context exists."""

from __future__ import annotations

import io

import fitz
import pytest

from preflight.checks import CheckResult, Severity
from preflight.checks.dimensions import check_dimensions
from preflight.checks.image_resolution import check_image_resolution
from preflight.document import Document, UploadedFile
from preflight.formats import get_format
from tests.conftest import A5_W_PT, A5_H_PT, _make_pdf_with_trimbox


def test_bbox_none_on_check_result_by_default():
    r = CheckResult(check_name="foo", severity=Severity.INFO, message="ok")
    assert r.bbox is None


def _pdf_with_safe_zone_violation() -> bytes:
    """PDF with text just inside the TrimBox edge (< 3mm safe zone)."""
    bleed_pt = 2.0 / 25.4 * 72.0
    media_w = A5_W_PT + 2 * bleed_pt
    media_h = A5_H_PT + 2 * bleed_pt
    doc = fitz.open()
    page = doc.new_page(width=media_w, height=media_h)
    trim_rect = fitz.Rect(bleed_pt, bleed_pt, bleed_pt + A5_W_PT, bleed_pt + A5_H_PT)
    page.set_trimbox(trim_rect)
    # Place text 1mm (2.83pt) from TrimBox edge — inside the 3mm safe zone
    page.insert_text((trim_rect.x0 + 2.0, trim_rect.y0 + 20.0), "Texte trop proche du bord", fontsize=8)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def test_safe_zone_violation_has_bbox():
    f = UploadedFile(name="close.pdf", data=_pdf_with_safe_zone_violation())
    doc = Document.from_upload([f])
    results = check_dimensions(doc, get_format("A5"))
    violation_results = [
        r for r in results
        if "zone tranquille" in r.message and r.bbox is not None
    ]
    assert violation_results, "safe zone violation CheckResult should have a bbox"
    bbox = violation_results[0].bbox
    assert len(bbox) == 4
    x0, y0, x1, y1 = bbox
    assert x1 > x0 and y1 > y0, "bbox must be non-degenerate"


def _pdf_with_small_image() -> bytes:
    """PDF with a tiny (low effective DPI) embedded image."""
    doc = fitz.open()
    page = doc.new_page(width=A5_W_PT, height=A5_H_PT)
    # Create a tiny PNG (10×10 px) and insert it at a large rect → low DPI
    from PIL import Image as PILImage
    img = PILImage.new("RGB", (10, 10), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    # Insert at 100pt×100pt → effective DPI ≈ (10/100)*72 = 7.2 DPI → ERROR
    page.insert_image(fitz.Rect(50, 50, 150, 150), stream=buf.getvalue())
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def test_low_res_image_has_bbox():
    f = UploadedFile(name="lowres.pdf", data=_pdf_with_small_image())
    doc = Document.from_upload([f])
    results = check_image_resolution(doc)
    error_results = [r for r in results if r.severity is Severity.ERROR]
    assert error_results, "low DPI image must produce an ERROR"
    # At least the error result for the low-res image should have a bbox
    assert any(r.bbox is not None for r in error_results), (
        "low-res image ERROR CheckResult should carry its bbox on the page"
    )


def test_high_res_pdf_images_have_no_bbox():
    """Images that pass the resolution check should not carry a bbox (nothing to highlight)."""
    # A plain PDF with no embedded images → no image_resolution results with bbox
    doc = fitz.open()
    doc.new_page(width=A5_W_PT, height=A5_H_PT)
    out = io.BytesIO()
    doc.save(out)
    f = UploadedFile(name="clean.pdf", data=out.getvalue())
    document = Document.from_upload([f])
    results = check_image_resolution(document)
    assert all(r.bbox is None for r in results)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
.venv/bin/pytest tests/test_checks_bbox.py -v
```

Expected: `test_bbox_none_on_check_result_by_default` PASSES (bbox field not added yet → AttributeError on others), or multiple FAILs.

- [ ] **Step 3: Add `bbox` field to `CheckResult`**

In `preflight/checks/__init__.py`, add `bbox` to the dataclass:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class CheckResult:
    check_name: str
    severity: Severity
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None

    @property
    def is_error(self) -> bool:
        return self.severity is Severity.ERROR


__all__ = ["Severity", "CheckResult"]
```

- [ ] **Step 4: Update `safe_zone_violations_mm` to return bbox**

In `preflight/document.py`, in `PdfPage.safe_zone_violations_mm()`, add `bbox` to each violation dict. Replace the `violations.append(...)` call:

```python
            violations.append({
                "text": text.strip()[:50].replace("\n", " "),
                "min_dist_mm": min_dist,
                "bbox": (block_rect.x0, block_rect.y0, block_rect.x1, block_rect.y1),
            })
```

- [ ] **Step 5: Propagate bbox in `check_dimensions` safe-zone violation result**

In `preflight/checks/dimensions.py`, in `_pdf_box_consistency()`, update the safe-zone violation result to carry the bbox. Replace the violation CheckResult construction:

```python
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
```

- [ ] **Step 6: Update `check_image_resolution` to use `get_image_info()` and populate bbox**

Replace the entire `check_image_resolution` function body in `preflight/checks/image_resolution.py`:

```python
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
            bbox = info.get("bbox")  # fitz.Rect or 4-tuple
            if bbox is not None:
                placed_w_pt = bbox[2] - bbox[0]  # x1 - x0
                dpi = (img_width_px / placed_w_pt) * 72.0 if placed_w_pt > 0 else 0.0
                bbox_tuple = (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
            else:
                page_width_pt = page_obj.rect.width
                dpi = (img_width_px / page_width_pt) * 72.0 if page_width_pt > 0 else 0.0
                bbox_tuple = None
            dpi_list.append((dpi, bbox_tuple))

        if not dpi_list:
            continue

        min_dpi = min(d for d, _ in dpi_list)
        avg_dpi = sum(d for d, _ in dpi_list) / len(dpi_list)

        # Find bbox of the lowest-DPI image for annotation
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
            result_bbox = None  # no issue to highlight

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
```

- [ ] **Step 7: Run bbox tests**

```bash
.venv/bin/pytest tests/test_checks_bbox.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 8: Run full suite**

```bash
.venv/bin/pytest -q
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
rtk git add preflight/checks/__init__.py preflight/document.py preflight/checks/dimensions.py preflight/checks/image_resolution.py tests/test_checks_bbox.py
rtk git commit -m "feat: add bbox field to CheckResult and populate from safe-zone and image-resolution checks"
```

---

## Task 3: DocumentSnapshot Pre-Parse Cache

**Files:**
- Create: `preflight/snapshot.py`
- Modify: `preflight/pipeline.py`
- Modify: `preflight/checks/logos.py`
- Modify: `preflight/checks/qrcode.py`
- Modify: `preflight/checks/image_resolution.py`
- Modify: `preflight/checks/font_embedding.py`
- Modify: `tests/test_snapshot.py` (new)
- Modify: `tests/test_checks_visual.py`
- Modify: `tests/test_logos.py`

### Background

Currently `check_qr` and `check_logos` each call `page.render(dpi=300)` independently — for a 2-page document that is 4 renders. `check_font_embedding` calls `page.get_fonts(full=True)` on each page. `check_image_resolution` (after Task 2) calls `get_image_info()`. None of these results are shared. `DocumentSnapshot` is built once by `run_all_checks` and passed to each check that needs it, eliminating redundant computation.

The snapshot is an implementation detail of the pipeline — it is not part of the public `CheckContext` interface.

- [ ] **Step 1: Write the failing snapshot tests**

Create `tests/test_snapshot.py`:

```python
"""Tests for DocumentSnapshot build and caching."""

from __future__ import annotations

import io

import fitz
import pytest

from preflight.document import Document, UploadedFile
from preflight.snapshot import DocumentSnapshot
from tests.conftest import A5_W_PT, A5_H_PT, _make_pdf


def test_snapshot_build_pdf_has_renders():
    f = UploadedFile(name="flyer.pdf", data=_make_pdf(pages=1))
    doc = Document.from_upload([f])
    snap = DocumentSnapshot.build(doc)
    assert 0 in snap.page_renders
    from PIL import Image
    assert isinstance(snap.page_renders[0], Image.Image)


def test_snapshot_build_two_page_pdf():
    f = UploadedFile(name="flyer.pdf", data=_make_pdf(pages=2))
    doc = Document.from_upload([f])
    snap = DocumentSnapshot.build(doc)
    assert set(snap.page_renders.keys()) == {0, 1}
    assert set(snap.page_fonts.keys()) == {0, 1}


def test_snapshot_build_image_doc(png_a5_300dpi):
    doc = Document.from_upload([png_a5_300dpi])
    snap = DocumentSnapshot.build(doc)
    assert 0 in snap.page_renders
    # Image pages: page_fonts and page_image_info are empty for non-PDF
    assert 0 not in snap.page_fonts


def test_snapshot_page_renders_are_300dpi():
    """Rendered images should be 300dpi-sized for PDF pages."""
    # A5 at 300 DPI: 148mm = 1748px, 210mm = 2480px (±1 for rounding)
    f = UploadedFile(name="flyer.pdf", data=_make_pdf(pages=1))
    doc = Document.from_upload([f])
    snap = DocumentSnapshot.build(doc)
    img = snap.page_renders[0]
    w, h = img.size
    assert 1700 < w < 1800, f"width {w}px expected ~1748px for A5 at 300dpi"
    assert 2400 < h < 2560, f"height {h}px expected ~2480px for A5 at 300dpi"
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
.venv/bin/pytest tests/test_snapshot.py -v
```

Expected: `ModuleNotFoundError: No module named 'preflight.snapshot'`

- [ ] **Step 3: Create `preflight/snapshot.py`**

```python
"""DocumentSnapshot — pre-parsed, per-run cache of expensive document operations.

Built once by the pipeline before the check loop starts. Passed to checks
that need it so they can skip redundant re-computation (page renders, font
lists, per-image geometry).

Only PDF pages contribute to page_image_info and page_fonts — image-mode
documents leave those dicts empty.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image

from preflight.document import Document

SNAPSHOT_RENDER_DPI = 300


@dataclass
class DocumentSnapshot:
    # page index → 300dpi render (PDF: rasterized; image: raw image)
    page_renders: dict[int, Image.Image] = field(default_factory=dict)
    # page index → get_image_info(hashes=False) result (PDF pages only)
    page_image_info: dict[int, list[dict]] = field(default_factory=dict)
    # page index → get_fonts(full=True) result (PDF pages only)
    page_fonts: dict[int, list] = field(default_factory=dict)

    @classmethod
    def build(cls, document: Document) -> "DocumentSnapshot":
        snap = cls()
        for page in document.pages:
            if page.source == "pdf":
                snap.page_renders[page.index] = page.render(dpi=SNAPSHOT_RENDER_DPI)
                snap.page_image_info[page.index] = page._page.get_image_info(hashes=False)
                snap.page_fonts[page.index] = page._page.get_fonts(full=True)
            else:
                snap.page_renders[page.index] = page.render()
        return snap


__all__ = ["DocumentSnapshot", "SNAPSHOT_RENDER_DPI"]
```

- [ ] **Step 4: Run snapshot tests**

```bash
.venv/bin/pytest tests/test_snapshot.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Update `check_logos` to accept and use the snapshot**

In `preflight/checks/logos.py`, add `snapshot` parameter and use `snapshot.page_renders`:

```python
from preflight.snapshot import DocumentSnapshot

def check_logos(
    document: Document,
    library: LogoLibrary,
    print_method: PrintMethod,
    snapshot: DocumentSnapshot,
    *,
    threshold: int = DEFAULT_THRESHOLD,
) -> list[CheckResult]:
    if library.is_empty:
        return [
            CheckResult(
                check_name="logos",
                severity=Severity.INFO,
                message=(
                    "Bibliothèque de logos non configurée — vérification manuelle requise pour "
                    "le Cartouche Info-tri (≥ 8 mm) et le logo getinside."
                ),
            )
        ]

    expected: dict[str, str] = dict(REQUIRED_CATEGORIES)
    if print_method == "Imprimé par la marque":
        expected.update(SELF_PRINT_CATEGORIES)

    aggregated: dict[str, int] = {}
    for page in document.pages:
        rendered = snapshot.page_renders[page.index]
        per_cat = library.all_distances(rendered)
        for cat, match in per_cat.items():
            if cat not in aggregated or match.distance < aggregated[cat]:
                aggregated[cat] = match.distance

    # ... rest of function unchanged (results construction) ...
```

Keep the results construction section identical to the original.

- [ ] **Step 6: Update `check_qr` to accept and use the snapshot**

In `preflight/checks/qrcode.py`, add `snapshot` parameter:

```python
from preflight.snapshot import DocumentSnapshot, SNAPSHOT_RENDER_DPI

def check_qr(document: Document, snapshot: DocumentSnapshot) -> list[CheckResult]:
    results: list[CheckResult] = []
    target = normalize(BASE_URL)

    detections_per_page: list[tuple[int, list]] = []
    for page in document.pages:
        image = snapshot.page_renders[page.index]
        dpi = float(SNAPSHOT_RENDER_DPI) if page.source == "pdf" else (page.dpi() or 72.0)
        detections_per_page.append((page.index, detect_qr_codes(image, dpi=dpi)))

    # ... rest of function unchanged ...
```

- [ ] **Step 7: Update `check_image_resolution` to use snapshot.page_image_info**

In `preflight/checks/image_resolution.py`, add `snapshot` parameter. Replace the `page_obj.get_image_info()` call with the snapshot:

```python
from preflight.snapshot import DocumentSnapshot

def check_image_resolution(document: Document, snapshot: DocumentSnapshot) -> list[CheckResult]:
    results: list[CheckResult] = []

    for page in document.pages:
        if page.source != "pdf":
            continue

        image_infos = snapshot.page_image_info.get(page.index, [])

        if not image_infos:
            continue

        # ... rest of function identical to Task 2 version, just using image_infos directly ...
```

- [ ] **Step 8: Update `check_font_embedding` to use snapshot.page_fonts**

In `preflight/checks/font_embedding.py`, add `snapshot` parameter:

```python
from preflight.snapshot import DocumentSnapshot

def check_font_embedding(document: Document, snapshot: DocumentSnapshot) -> list[CheckResult]:
    results: list[CheckResult] = []

    if document.kind != "pdf":
        return results

    try:
        for page_num in range(len(document.pages)):
            font_list = snapshot.page_fonts.get(page_num, [])
            for font_info in font_list:
                font_name = font_info[1] if len(font_info) > 1 else ""
                font_subset = font_info[0] if len(font_info) > 0 else ""

                if not font_name:
                    continue

                is_subset = len(font_name) > 6 and font_name[:6].isupper() and font_name[6] == "+"
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
```

- [ ] **Step 9: Update `pipeline.py` to build snapshot and pass it**

In `preflight/pipeline.py`, add the snapshot import and build it in both `run_all_checks` variants. Replace relevant `check_*` calls:

```python
from preflight.snapshot import DocumentSnapshot

def run_all_checks(
    document: Document,
    context: CheckContext,
    *,
    logo_library: LogoLibrary | None = None,
) -> list[CheckResult]:
    if logo_library is None:
        logo_library = LogoLibrary(LOGO_LIBRARY_ROOT)

    snapshot = DocumentSnapshot.build(document)

    results: list[CheckResult] = []
    results.extend(check_dimensions(document, context.format_spec))
    results.extend(check_bleed(document))
    results.extend(check_colorspace(document))
    results.extend(check_image_resolution(document, snapshot))
    results.extend(check_transparency(document))
    results.extend(check_qr(document, snapshot))
    results.extend(check_logos(document, logo_library, context.print_method, snapshot))

    results.extend(check_font_embedding(document, snapshot))
    results.extend(check_linked_images(document))
    results.extend(check_spot_colors(document))
    results.extend(check_page_boxes(document))

    document_text = all_text(document)
    detected, _ = detect_industry(document_text)
    effective_industry = context.industry if context.industry else detected

    results.extend(check_advertiser(document_text))
    results.extend(check_offer(document_text))
    results.extend(check_printer(document_text, context.print_method))
    results.extend(check_industry(document_text, effective_industry))

    return _apply_severity_overrides(results, context.severity_overrides)
```

Do the same for `run_all_checks_with_extraction` (identical snapshot build and passing pattern).

- [ ] **Step 10: Update test call sites for the new signatures**

In `tests/test_checks_visual.py`, any call to `check_qr(doc)` or `check_logos(doc, lib, method)` must be updated to pass a snapshot. Find all call sites:

```bash
grep -n "check_qr\|check_logos" tests/test_checks_visual.py tests/test_logos.py
```

For each call site, build a snapshot first:

```python
from preflight.snapshot import DocumentSnapshot
# ...
snap = DocumentSnapshot.build(doc)
results = check_qr(doc, snap)
# or
results = check_logos(doc, library, print_method, snap)
```

In `tests/test_checks_bbox.py`, update `check_image_resolution` calls:

```python
snap = DocumentSnapshot.build(document)
results = check_image_resolution(document, snap)
```

- [ ] **Step 11: Run full suite**

```bash
.venv/bin/pytest -q
```

Expected: all tests pass.

- [ ] **Step 12: Commit**

```bash
rtk git add preflight/snapshot.py preflight/pipeline.py preflight/checks/logos.py preflight/checks/qrcode.py preflight/checks/image_resolution.py preflight/checks/font_embedding.py tests/test_snapshot.py tests/test_checks_visual.py tests/test_logos.py tests/test_checks_bbox.py
rtk git commit -m "feat: add DocumentSnapshot to cache page renders and image/font data across checks"
```

---

## Self-Review

**Spec coverage:**
- Severity overrides → Task 1 ✓
- bbox on CheckResult → Task 2 ✓
- DocumentSnapshot cache → Task 3 ✓
- bbox populated in dimensions (safe zone) → Task 2 step 4–5 ✓
- bbox populated in image_resolution (low-res images) → Task 2 step 6 ✓
- Snapshot caches renders → Task 3 step 3 ✓
- Snapshot caches image info → Task 3 step 3 ✓
- Snapshot caches fonts → Task 3 step 3 ✓
- Pipeline builds snapshot once and passes it → Task 3 step 9 ✓
- Tests updated at all affected call sites → Task 3 step 10 ✓

**Placeholder scan:** No TBDs. All code blocks are complete.

**Type consistency:**
- `DocumentSnapshot` defined in Task 3 step 3, used in steps 5–9 with matching field names (`page_renders`, `page_image_info`, `page_fonts`)
- `bbox: tuple[float, float, float, float] | None` defined in Task 2 step 3, stored in steps 5 and 6 as `(float, float, float, float)` tuples ✓
- `severity_overrides: dict[str, Severity]` defined in Task 1 step 3, consumed by `_apply_severity_overrides(results, context.severity_overrides)` ✓
- `_apply_severity_overrides` creates new `CheckResult` — it must also forward the new `bbox` field added in Task 2. Update in Task 2 step 3 or add a note: after Task 2, `_apply_severity_overrides` must include `bbox=r.bbox` in the replacement `CheckResult` constructor call.

**Fix — `_apply_severity_overrides` must forward `bbox`:** The Task 1 implementation of `_apply_severity_overrides` creates replacement `CheckResult` objects. After Task 2 adds `bbox`, update that helper:

```python
def _apply_severity_overrides(
    results: list[CheckResult], overrides: dict[str, Severity]
) -> list[CheckResult]:
    if not overrides:
        return results
    return [
        CheckResult(
            check_name=r.check_name,
            severity=overrides[r.check_name] if r.check_name in overrides else r.severity,
            message=r.message,
            details=r.details,
            page=r.page,
            bbox=r.bbox,
        )
        for r in results
    ]
```

This should be done as part of Task 2 step 3 (when `bbox` is added to `CheckResult`).

---

## Verification

After all three tasks:

```bash
# Full test suite
.venv/bin/pytest -q

# Smoke test: run the app and upload a PDF
.venv/bin/streamlit run app.py --server.port 8766
```

For the app smoke test: upload any A5 flyer PDF and confirm results still display correctly. The `bbox` field is unused by the UI at this stage — it is available for future overlay rendering.
