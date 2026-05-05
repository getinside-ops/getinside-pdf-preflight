# Checks Cleanup & Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the failing test by restoring detail rendering, wire up `page_boxes` check, and remove 6 dead check modules + 1 duplicate import.

**Architecture:** Three independent tasks — test fix touches only `report_html.py`, page_boxes wiring touches `pipeline.py` + `report_html.py`, cleanup deletes files and removes dead imports from `pipeline.py`.

**Tech Stack:** Python 3.13, PyMuPDF (fitz), pytest

---

## File Map

| File | Action |
|---|---|
| `preflight/report_html.py` | Restore detail rendering loop (gray `#9ca3af`) + add `page_boxes` to `_CHECK_META` |
| `preflight/pipeline.py` | Add `check_page_boxes` calls in both `run_all_checks` functions, remove 5 dead imports + 1 duplicate |
| `preflight/checks/crop_marks.py` | Delete |
| `preflight/checks/linearized.py` | Delete |
| `preflight/checks/optional_content.py` | Delete |
| `preflight/checks/corrupted_objects.py` | Delete |
| `preflight/checks/metadata_stripping.py` | Delete |
| `preflight/checks/overprint.py` | Delete (stub, always returns `[]`) |

---

## Task 1: Fix failing test — restore detail rendering in `build_html_report`

**Files:**
- Modify: `preflight/report_html.py`
- Test: `tests/test_report_html.py`

The test `test_detail_text_rendered` creates a check with `details={"found": [210.0, 297.0]}` and asserts that `#9ca3af` and `"210"` appear in the HTML output. The helper `_fmt_detail_value` already formats `[210.0, 297.0]` → `"210 × 297 mm"` — it just needs to be called inside the per-result rendering loop.

- [ ] **Step 1: Run the failing test to confirm the baseline**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
.venv/bin/pytest tests/test_report_html.py::test_detail_text_rendered -v
```
Expected: FAIL — `assert '#9ca3af' in ...`

- [ ] **Step 2: Add detail rendering after each message line in `build_html_report`**

In `preflight/report_html.py`, find the per-result block (around line 116) that currently ends with:

```python
            parts.append(
                f"<div style='padding-left:16px;font-size:12.5px;line-height:1.6'>"
                f"<span style='color:{dot_color}'>·</span> "
                f"{page_badge}"
                f"<span style='color:{text_color}'>{escape(formatted_msg)}</span>"
                f"</div>"
            )
```

Replace it with:

```python
            detail_lines = ""
            if r.details:
                for k, v in r.details.items():
                    if k == "page":
                        continue
                    detail_lines += (
                        f"<div style='padding-left:28px;font-size:11.5px;color:#9ca3af'>"
                        f"{escape(k)}: {escape(_fmt_detail_value(v))}</div>"
                    )
            parts.append(
                f"<div style='padding-left:16px;font-size:12.5px;line-height:1.6'>"
                f"<span style='color:{dot_color}'>·</span> "
                f"{page_badge}"
                f"<span style='color:{text_color}'>{escape(formatted_msg)}</span>"
                f"</div>"
                f"{detail_lines}"
            )
```

- [ ] **Step 3: Run the test to verify it passes**

```bash
.venv/bin/pytest tests/test_report_html.py -v
```
Expected: all tests in `test_report_html.py` PASS.

- [ ] **Step 4: Commit**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
rtk git add preflight/report_html.py
rtk git commit -m "fix: restore detail rendering in HTML report (gray #9ca3af)"
```

---

## Task 2: Wire `page_boxes` into the pipeline

**Files:**
- Modify: `preflight/pipeline.py` (add 2 calls)
- Modify: `preflight/report_html.py` (add entry to `_CHECK_META`)

The import `from preflight.checks.page_boxes import check_page_boxes` already exists in `pipeline.py` (line 31). Just need to add the calls and register the label.

- [ ] **Step 1: Add `page_boxes` to `_CHECK_META` in `report_html.py`**

In `preflight/report_html.py`, add after the `"spot_colors"` entry (line 24):

```python
    "page_boxes":  ("", "PAGE BOXES"),
```

- [ ] **Step 2: Add `check_page_boxes` call to `run_all_checks` in `pipeline.py`**

In `run_all_checks` (around line 85), after the three new print checks:

```python
    results.extend(check_font_embedding(document))
    results.extend(check_linked_images(document))
    results.extend(check_spot_colors(document))
    results.extend(check_page_boxes(document))
```

Do the same in `run_all_checks_with_extraction` (same pattern, ~line 121).

- [ ] **Step 3: Run the full test suite**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
.venv/bin/pytest -q
```
Expected: all tests pass (the `page_boxes` check is PDF-only and skips gracefully for image fixtures).

- [ ] **Step 4: Commit**

```bash
rtk git add preflight/pipeline.py preflight/report_html.py
rtk git commit -m "feat: wire page_boxes check into pipeline"
```

---

## Task 3: Delete 6 dead check modules and clean duplicate import

**Files:**
- Delete: `preflight/checks/crop_marks.py`, `linearized.py`, `optional_content.py`, `corrupted_objects.py`, `metadata_stripping.py`, `overprint.py`
- Modify: `preflight/pipeline.py` — remove 6 import lines

- [ ] **Step 1: Delete the 6 dead files**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
rm preflight/checks/crop_marks.py \
   preflight/checks/linearized.py \
   preflight/checks/optional_content.py \
   preflight/checks/corrupted_objects.py \
   preflight/checks/metadata_stripping.py \
   preflight/checks/overprint.py
```

- [ ] **Step 2: Remove their imports + the duplicate `check_qr` import from `pipeline.py`**

Remove these 6 lines from `preflight/pipeline.py`:

```python
from preflight.checks.corrupted_objects import check_corrupted_objects
from preflight.checks.crop_marks import check_crop_marks
from preflight.checks.linearized import check_linearized
from preflight.checks.optional_content import check_optional_content
from preflight.checks.overprint import check_overprint
from preflight.checks.qrcode import check_qr   # second/duplicate occurrence only
```

The first `from preflight.checks.qrcode import check_qr` (line 33) stays. Remove only the duplicate at line 36.

- [ ] **Step 3: Run the full test suite**

```bash
.venv/bin/pytest -q
```
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
rtk git add preflight/pipeline.py
rtk git commit -m "chore: remove 6 dead check modules and duplicate import"
```
