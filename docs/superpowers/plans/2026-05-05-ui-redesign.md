# UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Print Preflight UI into a two-column layout with collapsible check cards, a fixed top bar with inline controls, and a consistent Lucide SVG icon system (no emoji).

**Architecture:** `app.py` is restructured into a top-bar + two-column layout (left: preview + metadata, right: verdict + cards). `report_html.py` is updated to emit `<details>`/`<summary>` collapsible cards with colored left borders. All icons centralised in a single `LUCIDE_ICONS` dict at the top of `app.py`; no emoji anywhere in the UI.

**Tech Stack:** Python, Streamlit >= 1.57, HTML/CSS injected via `st.markdown(unsafe_allow_html=True)`.

---

## File Map

| File | Change |
|---|---|
| `app.py` | Full restructure: single icon dict, remove sidebar, inline controls, two-column layout |
| `preflight/report_html.py` | Replace div sections with `<details>` collapsible cards + colored left borders |
| `tests/test_report_html.py` | Add tests for collapsible behavior and border colors |

---

## Task 1: Fix icon infrastructure — single `LUCIDE_ICONS` dict

**Files:**
- Modify: `app.py` (lines 31–147 — remove both `LUCIDE_ICONS` dicts and both `_lucide_icon` definitions)

The bug: `LUCIDE_ICONS` is defined at line 31 (with `check_circle`, `alert_triangle`, `x_circle`) and redefined at line 139 (with only `search`, `info`). The function `_lucide_icon` is also defined twice. The second definition silently drops the verdict icons.

Fix: delete both definitions and replace with one dict and one function at the top of the file.

- [ ] **Step 1: Open `app.py` and remove lines 31–40 (first LUCIDE_ICONS dict + first _lucide_icon)**

Delete this block entirely:
```python
LUCIDE_ICONS = {
    "check_circle": """<svg ...""",
    "alert_triangle": """<svg ...""",
    "x_circle": """<svg ...""",
}


def _lucide_icon(name: str) -> str:
    icon = LUCIDE_ICONS.get(name, "")
    return f'<span style="display:inline-flex;vertical-align:middle">{icon}</span>'
```

- [ ] **Step 2: Remove lines 139–147 (second LUCIDE_ICONS dict + second _lucide_icon)**

Delete this block entirely:
```python
LUCIDE_ICONS = {
    "search": """<svg ...""",
    "info": """<svg ...""",
}


def _lucide_icon(name: str) -> str:
    icon = LUCIDE_ICONS.get(name, "")
    return f'<span style="display:inline-flex;vertical-align:middle">{icon}</span>'
```

- [ ] **Step 3: Add the unified icon dict and function at the top of `app.py`, after the imports and `st.set_page_config` call**

Insert this block (after the `st.set_page_config(...)` call, before the CSS `st.markdown`):

```python
LUCIDE_ICONS: dict[str, str] = {
    "check_circle": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "alert_triangle": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "x_circle": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
    "info": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
    "printer": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect width="12" height="8" x="6" y="14"/></svg>',
    "upload": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',
    "maximize_2": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>',
    "settings": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 1 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>',
}


def _lucide_icon(name: str, size: int = 18) -> str:
    svg = LUCIDE_ICONS.get(name, "")
    if size != 18:
        svg = svg.replace('width="18"', f'width="{size}"').replace('height="18"', f'height="{size}"')
        svg = svg.replace('width="16"', f'width="{size}"').replace('height="16"', f'height="{size}"')
    return f'<span style="display:inline-flex;vertical-align:middle">{svg}</span>'
```

- [ ] **Step 4: Run the app briefly to confirm no SVG code leaks into the page**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
source .venv/bin/activate
.venv/bin/streamlit run app.py --server.port 8766 &
sleep 3 && kill %1
```

Expected: app starts without Python errors in stderr.

- [ ] **Step 5: Commit**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
rtk git add app.py
rtk git commit -m "fix: merge duplicate LUCIDE_ICONS dicts into single source of truth"
```

---

## Task 2: Collapsible check cards in `report_html.py`

**Files:**
- Modify: `preflight/report_html.py`
- Modify: `tests/test_report_html.py`

Each check group becomes a `<details>`/`<summary>` card with a colored left border. ERROR and WARNING groups are open by default; INFO groups are collapsed.

- [ ] **Step 1: Add 3 failing tests to `tests/test_report_html.py`**

Append to the end of the file:

```python
def test_error_card_is_open_by_default(ctx):
    results = [_r("dimensions", Severity.ERROR, "Taille incorrecte")]
    html = build_html_report(results, ctx)
    assert "<details open>" in html


def test_ok_card_is_collapsed_by_default(ctx):
    results = [_r("colorspace", Severity.INFO, "OK")]
    html = build_html_report(results, ctx)
    assert "<details>" in html
    assert "<details open>" not in html


def test_error_card_has_red_left_border(ctx):
    results = [_r("dimensions", Severity.ERROR, "Taille incorrecte")]
    html = build_html_report(results, ctx)
    assert "border-left:3px solid #dc2626" in html


def test_warning_card_has_amber_left_border(ctx):
    results = [_r("colorspace", Severity.WARNING, "Couleur non CMJN")]
    html = build_html_report(results, ctx)
    assert "border-left:3px solid #d97706" in html


def test_ok_card_has_green_left_border(ctx):
    results = [_r("logos", Severity.INFO, "Logo détecté")]
    html = build_html_report(results, ctx)
    assert "border-left:3px solid #16a34a" in html


def test_warning_card_is_open_by_default(ctx):
    results = [_r("colorspace", Severity.WARNING, "Couleur non CMJN")]
    html = build_html_report(results, ctx)
    assert "<details open>" in html
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
source .venv/bin/activate
.venv/bin/pytest tests/test_report_html.py -v
```

Expected: 6 new tests FAIL, 9 existing tests PASS.

- [ ] **Step 3: Replace `build_html_report` in `preflight/report_html.py`**

Add these two new dicts just below `_SEV_COLORS` (around line 33):

```python
_SEV_BORDER: dict[Severity, str] = {
    Severity.ERROR:   "#dc2626",
    Severity.WARNING: "#d97706",
    Severity.INFO:    "#16a34a",
}

_SEV_PILL: dict[Severity, tuple[str, str]] = {
    Severity.ERROR:   ("#fee2e2", "#dc2626"),
    Severity.WARNING: ("#fef3c7", "#92400e"),
    Severity.INFO:    ("#dcfce7", "#166534"),
}
```

Then replace the entire `build_html_report` function with:

```python
def build_html_report(results: list[CheckResult], context: CheckContext) -> str:
    """Return a self-contained HTML string for the preflight report."""
    header = escape(
        f"Format : {context.format_spec.name}"
        f"  ·  Industrie : {context.industry}"
        f"  ·  {context.print_method}"
    )

    parts: list[str] = [
        "<div style='border:1px solid #e5e7eb;background:#f9fafb;border-radius:8px;"
        "padding:10px 14px;margin-bottom:12px;"
        "font-family:Inter,ui-sans-serif,system-ui,sans-serif;"
        f"font-size:12px;color:#6b7280'>{header}</div>",
        "<div style='font-family:Inter,ui-sans-serif,system-ui,sans-serif'>",
    ]

    groups: dict[str, list[CheckResult]] = {}
    for r in results:
        groups.setdefault(r.check_name, []).append(r)

    ordered_keys = (
        [k for k in _CHECK_ORDER if k in groups]
        + [k for k in groups if k not in _CHECK_ORDER]
    )

    for name in ordered_keys:
        items = groups[name]
        worst = _group_worst(items)
        _, label = _CHECK_META.get(name, ("", name.upper()))

        e_count = sum(1 for r in items if r.severity is Severity.ERROR)
        w_count = sum(1 for r in items if r.severity is Severity.WARNING)

        border_color = _SEV_BORDER[worst]
        pill_bg, pill_fg = _SEV_PILL[worst]
        open_attr = " open" if worst is not Severity.INFO else ""

        if worst is Severity.ERROR:
            pill_text = f"{e_count} erreur{'s' if e_count > 1 else ''}"
        elif worst is Severity.WARNING:
            pill_text = f"{w_count} avertissement{'s' if w_count > 1 else ''}"
        else:
            pill_text = "OK"

        parts.append(
            f"<div style='margin-bottom:8px;border:1px solid #e5e7eb;"
            f"border-left:3px solid {border_color};border-radius:8px;overflow:hidden'>"
            f"<details{open_attr}>"
            f"<summary style='cursor:pointer;padding:10px 14px;background:#f9fafb;"
            f"font-size:13px;font-weight:600;color:#111827;list-style:none;"
            f"display:flex;align-items:center;justify-content:space-between'>"
            f"<span>{escape(label)}</span>"
            f"<span style='background:{pill_bg};color:{pill_fg};font-size:11px;"
            f"font-weight:600;padding:2px 8px;border-radius:4px'>{pill_text}</span>"
            f"</summary>"
            f"<div style='padding:8px 14px'>"
        )

        for r in items:
            text_color, dot_color = _SEV_COLORS[r.severity]
            page_badge = ""
            if r.page is not None:
                page_badge = (
                    f"<span style='background:#f3f4f6;color:#6b7280;font-size:11px;"
                    f"padding:1px 5px;border-radius:3px;margin-right:4px'>[p.{r.page + 1}]</span>"
                )
            formatted_msg = _format_message(r)
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
                f"<div style='padding:4px 0;font-size:12.5px;line-height:1.6'>"
                f"<span style='color:{dot_color}'>·</span> "
                f"{page_badge}"
                f"<span style='color:{text_color}'>{escape(formatted_msg)}</span>"
                f"</div>"
                f"{detail_lines}"
            )

        parts.append("</div></details></div>")

    parts.append("</div>")
    return "\n".join(parts)
```

- [ ] **Step 4: Run all report_html tests to confirm they pass**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
source .venv/bin/activate
.venv/bin/pytest tests/test_report_html.py -v
```

Expected: 15 tests PASS (9 existing + 6 new).

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
.venv/bin/pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
rtk git add preflight/report_html.py tests/test_report_html.py
rtk git commit -m "feat: collapsible check cards with colored left borders in HTML report"
```

---

## Task 3: Remove sidebar, add inline controls with collapse

**Files:**
- Modify: `app.py` (sidebar section + main panel header, approximately lines 100–135)

The sidebar is removed. Controls move to an inline `st.columns` row at the top of the page. When results are already stored in session state, controls collapse to a compact summary line with a "Modifier" button.

- [ ] **Step 1: Replace the title + sidebar block**

Delete the entire sidebar block (lines ~100–119):
```python
st.sidebar.markdown("**🖨️ Paramètres**")
st.sidebar.divider()

format_name = st.sidebar.selectbox("Format", ...)
if format_name == "Custom":
    ...
industry = st.sidebar.selectbox("Industrie", ...)
print_method = st.sidebar.radio("Impression", ...)
```

And delete the `st.markdown("#### 🖨️ Print Preflight — Getinside")` title line.

Replace with this entire block:

```python
# ---------- Top bar -----------------------------------------------------------

st.markdown(
    f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:16px'>"
    f"<span style='color:#111827;font-size:16px;font-weight:700'>"
    f"{_lucide_icon('printer', 20)}&nbsp;Print Preflight — Getinside</span>"
    f"</div>",
    unsafe_allow_html=True,
)

# ---------- Controls ----------------------------------------------------------

has_stored_results = "results" in st.session_state and "context" in st.session_state
has_doc_data = "doc_name" in st.session_state and "doc_data" in st.session_state

if has_stored_results:
    ctx_stored = st.session_state["context"]
    format_spec = ctx_stored.format_spec
    industry = ctx_stored.industry
    print_method = ctx_stored.print_method
    col_summary, col_btn = st.columns([9, 1])
    with col_summary:
        st.markdown(
            f"<span style='color:#6b7280;font-size:13px'>"
            f"<b>{format_spec.name}</b> &nbsp;·&nbsp; {industry} &nbsp;·&nbsp; {print_method}</span>",
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("Modifier", key="modify_settings"):
            st.session_state.clear()
            st.rerun()
else:
    col_fmt, col_ind, col_print = st.columns([2, 2, 3])
    with col_fmt:
        format_name = st.selectbox("Format", options=FORMAT_NAMES, index=0)
        if format_name == "Custom":
            custom_w = st.number_input("Largeur (mm)", min_value=10, max_value=1000, value=148, step=1)
            custom_h = st.number_input("Hauteur (mm)", min_value=10, max_value=1000, value=210, step=1)
            format_spec = custom_format(float(custom_w), float(custom_h))
        else:
            format_spec = get_format(format_name)
    with col_ind:
        industry = st.selectbox("Industrie", options=INDUSTRY_NAMES)
    with col_print:
        print_method = st.radio(
            "Impression",
            options=["Imprimé par getinside", "Imprimé par la marque"],
        )
```

Also remove the `has_stored_results` and `has_doc_data` lines in the `# --- Run ---` section (around line 346) since they are now defined above.

- [ ] **Step 2: Remove the `layout="wide"` workaround comment if present; keep `layout="wide"` in `st.set_page_config`**

Confirm `st.set_page_config` still has `layout="wide"` — no change needed.

- [ ] **Step 3: Start the app and verify controls display correctly**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
source .venv/bin/activate
.venv/bin/streamlit run app.py --server.port 8766
```

Check:
- No sidebar visible
- Three inline controls (Format / Industrie / Impression) in a row
- Title with printer icon (no emoji)
- Upload file, run analysis → controls collapse to summary line + "Modifier" button
- Click "Modifier" → controls reappear, results cleared

- [ ] **Step 4: Run full test suite**

```bash
.venv/bin/pytest -q
```

Expected: all tests pass (UI changes don't affect unit tests).

- [ ] **Step 5: Commit**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
rtk git add app.py
rtk git commit -m "feat: remove sidebar, add inline controls with collapse-to-summary on results"
```

---

## Task 4: Two-column results layout

**Files:**
- Modify: `app.py` — `_display_analysis_results` function and the verdict banner code

Left column (40%): page thumbnails stacked vertically + metadata card + OCR expander.  
Right column (60%): verdict banner + collapsible check cards.

- [ ] **Step 1: Replace the `_display_analysis_results` function entirely**

Find and replace the entire `_display_analysis_results` function (from `def _display_analysis_results(` to the last line of the function body):

```python
def _display_analysis_results(document, results, context, extraction_info, doc_name) -> None:
    col_left, col_right = st.columns([4, 6])

    with col_left:
        # --- Page thumbnails ---
        for page in document.pages:
            st.caption(f"Page {page.index + 1} — {page.source.upper()}")
            try:
                preview = page.render(dpi=72) if page.source == "pdf" else page.render()
                st.image(preview, use_container_width=True)
                if st.button("Agrandir", key=f"view_page_{page.index}"):
                    st.session_state[f"show_page_{page.index}"] = True
            except Exception as exc:
                st.caption(f"Aperçu indisponible : {exc}")

        # --- Full-page expanders ---
        for page_idx in range(len(document.pages)):
            if st.session_state.get(f"show_page_{page_idx}", False):
                with st.expander(f"Page {page_idx + 1} (plein format)", expanded=True):
                    try:
                        full_img = document.pages[page_idx].render(dpi=300)
                        st.image(full_img, use_container_width=True)
                    except Exception as exc:
                        st.error(f"Impossible d'afficher : {exc}")
                if st.button("Fermer", key=f"close_page_{page_idx}"):
                    st.session_state[f"show_page_{page_idx}"] = False
                    st.rerun()

        # --- Metadata card ---
        _render_key_info_banner(doc_name, results, document)

        # --- OCR details ---
        if extraction_info:
            with st.expander("Détails techniques (OCR)"):
                st.markdown("**Paramètres OCR utilisés:**")
                st.markdown(f"- **DPI:** {extraction_info.ocr_settings.dpi}")
                st.markdown(f"- **Langue:** {extraction_info.ocr_settings.lang}")
                st.markdown(f"- **Config:** `{extraction_info.ocr_settings.config}`")
                st.markdown(f"- **Prétraitement:** {', '.join(extraction_info.ocr_settings.preprocessing)}")
                st.markdown("---")
                st.markdown("**Texte détecté par page:**")
                for pt in extraction_info.pages:
                    st.markdown(f"**Page {pt.page_index + 1}** — Méthode: `{pt.method.value}`")
                    if pt.text.strip():
                        st.code(pt.text.strip()[:2000] + ("..." if len(pt.text.strip()) > 2000 else ""), language=None)
                    else:
                        st.caption("(aucun texte détecté)")
                st.markdown("---")
                st.markdown("**Texte complet concaténé:**")
                st.code(extraction_info.text_used[:3000] + ("..." if len(extraction_info.text_used) > 3000 else ""), language=None)

    with col_right:
        # --- Verdict banner ---
        counts = summarize(results)
        verdict = overall_verdict(results)
        e = counts.get("error", 0)
        w = counts.get("warning", 0)
        i = counts.get("info", 0)

        if verdict == "fail":
            bg, color = "#fee2e2", "#dc2626"
            icon = _lucide_icon("x_circle")
            main = f"{icon} <b>{e} erreur{'s' if e > 1 else ''}</b>"
            if w:
                main += f" &nbsp;·&nbsp; {_lucide_icon('alert_triangle')} {w} avertissement{'s' if w > 1 else ''}"
        elif verdict == "review":
            bg, color = "#fef3c7", "#92400e"
            icon = _lucide_icon("alert_triangle")
            main = f"{icon} <b>{w} avertissement{'s' if w > 1 else ''}</b>"
        else:
            bg, color = "#dcfce7", "#166534"
            icon = _lucide_icon("check_circle")
            main = f"{icon} <b>Conforme</b> — prêt pour l'impression"

        st.markdown(
            f"<div style='background:{bg};border-radius:8px;padding:12px 16px;margin-bottom:12px'>"
            f"<span style='color:{color};font-size:14px'>{main}</span>"
            f"<span style='color:#6b7280;font-size:13px'>"
            f"&nbsp;&nbsp;·&nbsp;&nbsp;{_lucide_icon('info')} {i} info{'s' if i > 1 else ''}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # --- Check cards ---
        _render_html_report(results, context)
```

- [ ] **Step 2: Remove the old divider + OCR expander that followed `_render_html_report` in the previous version**

In the `# --- Run ---` section, find and delete these lines that are now dead (they were the old OCR block inside `_display_analysis_results`):
```python
    st.divider()

    ext_info = extraction_info
    if ext_info:
        with st.expander("🔧 Détails techniques (OCR)"):
            ...
    else:
        st.warning("Aucune donnée d'extraction disponible.")
```

These are now inside `_display_analysis_results` in the left column.

- [ ] **Step 3: Remove emoji from the empty-state caption at the bottom of `app.py`**

Find:
```python
    st.caption("📥 Déposez un PDF (1-2 pages) ou jusqu'à 2 images PNG/JPEG.")
```

Replace with:
```python
    st.caption("Déposez un PDF (1-2 pages) ou jusqu'à 2 images PNG/JPEG.")
```

- [ ] **Step 4: Start the app and test the full flow**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
source .venv/bin/activate
.venv/bin/streamlit run app.py --server.port 8766
```

Upload a PDF and verify:
- Left column: page thumbnails stacked, "Agrandir" button, metadata card, OCR expander at bottom
- Right column: verdict banner with Lucide icons (no emoji, no raw SVG code), collapsible check cards with colored left borders
- ERROR/WARNING cards open by default; OK cards collapsed
- "Agrandir" expands page below the thumbnail in the left column
- "Modifier" clears session and reloads controls

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
rtk git add app.py
rtk git commit -m "feat: two-column layout — page preview left, verdict + check cards right"
```
