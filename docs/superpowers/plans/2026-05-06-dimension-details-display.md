# Dimension Details Display — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace raw technical keys in check detail lines with French labels, and append units to scalar values.

**Architecture:** Two dicts (`_DETAIL_LABELS_FR`, `_DETAIL_UNITS_FR`) added to `report_html.py`. The detail rendering loop (lines 153-160) is updated to use them. A value translation dict handles `kind` string values. All other behaviour is unchanged — unknown keys fall back to their raw name.

**Tech Stack:** Python, `preflight/report_html.py`, pytest.

---

### Task 1: Add failing tests for French labels and units

**Files:**
- Modify: `tests/test_report_html.py`

- [ ] **Step 1: Add tests at the bottom of `tests/test_report_html.py`**

```python
def test_detail_label_translated_to_french(ctx):
    results = [_r("dimensions", Severity.INFO, "OK", details={"found_mm": (105.0, 148.0)})]
    html = build_html_report(results, ctx)
    assert "Dimensions détectées" in html
    assert "found_mm" not in html


def test_detail_label_fallback_for_unknown_key(ctx):
    results = [_r("dimensions", Severity.ERROR, "Err", details={"unknown_key": 42})]
    html = build_html_report(results, ctx)
    assert "unknown_key" in html


def test_detail_scalar_unit_appended(ctx):
    results = [_r("dimensions", Severity.ERROR, "Err", details={"tolerance_mm": 1})]
    html = build_html_report(results, ctx)
    assert "1 mm" in html


def test_detail_dpi_unit_appended(ctx):
    results = [_r("image_resolution", Severity.ERROR, "Err", details={"dpi": 72, "min_dpi": 300})]
    html = build_html_report(results, ctx)
    assert "72 DPI" in html
    assert "300 DPI" in html


def test_detail_kind_value_translated(ctx):
    results = [_r("dimensions", Severity.INFO, "OK", details={"kind": "final"})]
    html = build_html_report(results, ctx)
    assert "format final" in html
    assert ">final<" not in html


def test_detail_kind_bleed_translated(ctx):
    results = [_r("dimensions", Severity.INFO, "OK", details={"kind": "bleed"})]
    html = build_html_report(results, ctx)
    assert "format avec fond perdu" in html
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
.venv/bin/pytest tests/test_report_html.py -k "translated or unit_appended or kind_value or kind_bleed or fallback_for_unknown" -v
```

Expected: all 6 new tests FAIL (labels still raw, no units, kind not translated).

---

### Task 2: Implement the label/unit/value translation in `report_html.py`

**Files:**
- Modify: `preflight/report_html.py`

- [ ] **Step 1: Add the two mapping dicts after the `_SEV_ICON` dict (after line 45)**

Insert after the closing brace of `_SEV_ICON`:

```python
_DETAIL_LABELS_FR: dict[str, str] = {
    "found_mm":            "Dimensions détectées",
    "expected_final_mm":   "Format final attendu",
    "expected_bleed_mm":   "Format avec fond perdu attendu",
    "tolerance_mm":        "Tolérance",
    "kind":                "Correspondance",
    "trim_box_mm":         "TrimBox (zone de découpe finale)",
    "media_box_mm":        "MediaBox (page entière, inclut fond perdu ou traits de coupe)",
    "violations_count":    "Éléments dans la zone tranquille",
    "min_dist_mm":         "Distance minimale au bord",
    "dpi":                 "Résolution détectée",
    "min_dpi":             "Résolution minimale requise",
    "short_side_mm":       "Côté le plus court",
}

_DETAIL_UNITS_FR: dict[str, str] = {
    "tolerance_mm":  "mm",
    "min_dist_mm":   "mm",
    "short_side_mm": "mm",
    "dpi":           "DPI",
    "min_dpi":       "DPI",
}

_KIND_VALUES_FR: dict[str, str] = {
    "final": "format final",
    "bleed": "format avec fond perdu",
}
```

- [ ] **Step 2: Update the detail rendering loop (currently lines 153-160)**

Replace:

```python
            if r.details:
                for k, v in r.details.items():
                    if k == "page":
                        continue
                    detail_lines += (
                        f"<div style='padding-left:28px;font-size:11.5px;color:#9ca3af'>"
                        f"{escape(k)}: {escape(_fmt_detail_value(v))}</div>"
                    )
```

With:

```python
            if r.details:
                for k, v in r.details.items():
                    if k == "page":
                        continue
                    label = _DETAIL_LABELS_FR.get(k, k)
                    if k == "kind":
                        v = _KIND_VALUES_FR.get(str(v), str(v))
                    formatted_v = _fmt_detail_value(v)
                    unit = _DETAIL_UNITS_FR.get(k, "")
                    if unit and not isinstance(v, (list, tuple)):
                        formatted_v = f"{formatted_v} {unit}"
                    detail_lines += (
                        f"<div style='padding-left:28px;font-size:11.5px;color:#9ca3af'>"
                        f"{escape(label)}: {escape(formatted_v)}</div>"
                    )
```

- [ ] **Step 3: Run the full test suite**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
.venv/bin/pytest tests/test_report_html.py -v
```

Expected: all tests PASS, including the 6 new ones and the existing `test_detail_text_rendered` (uses key `"found"` which is not in the mapping — fallback preserves it).

- [ ] **Step 4: Commit**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
rtk git add preflight/report_html.py tests/test_report_html.py
rtk git commit -m "feat: translate check detail labels to French with units"
```
