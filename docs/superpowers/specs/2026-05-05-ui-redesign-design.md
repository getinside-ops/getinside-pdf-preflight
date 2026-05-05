# UI Redesign — Print Preflight Tool

**Date:** 2026-05-05  
**Status:** Approved  
**Audience:** Internal Getinside ops staff

## Problem

The current UI makes it hard to spot check failures at a glance. Results are rendered as a dense wall of plain text. Raw SVG code leaks visually on the page due to a double-definition bug in `LUCIDE_ICONS` / `_lucide_icon`. The sidebar adds unnecessary chrome for an internal tool.

## Approach: Two-Column Redesign

### Layout

Three vertical zones, no sidebar:

1. **Top bar** — title + inline controls
2. **Upload strip** — file dropzone + run button (collapses once results are shown)
3. **Results area** — two-column split (`st.columns([4, 6])`)

### Zone 1 — Top bar

- Title: `Print Preflight — Getinside` (Lucide `printer` icon, no emoji)
- Format, Industrie, Impression as Streamlit widgets in a `st.columns` row, rendered above the file uploader
- Once results are shown, controls collapse into a single summary line: `A5 · Général · Imprimé par getinside` with a `[Modifier]` link that clears session state and reruns

### Zone 2 — Upload strip

- Streamlit `st.file_uploader` (label hidden) + `st.button("Lancer la vérification")`
- Hidden once results are displayed (controlled via `st.session_state`)

### Zone 3 — Results area (left 40% / right 60%)

**Left panel:**
- Page thumbnails stacked vertically, each with caption `Page 1 — PDF` and a Lucide `maximize-2` expand button
- Expanding a page opens `st.dialog` (or `st.expander` fallback) with 300 DPI render
- Metadata card below thumbnails: 2×2 grid showing Fichier, QR Code, Code Promo, Métadonnées (same data as current key-info banner)
- OCR technical details expander at the very bottom of the left panel

**Right panel:**
- **Verdict banner** (pinned top): colored strip showing worst severity + counts
  - Red: `[x-circle icon] 1 erreur · [triangle icon] 3 avertissements · [info icon] 13 infos`
  - Amber: `[triangle icon] 3 avertissements · [info icon] 13 infos`
  - Green: `[check-circle icon] Conforme — prêt pour l'impression`
- **Check cards** — one per check group, rendered as pure HTML via `report_html.py`:
  - Left border: 3px solid red / amber / green based on worst severity in the group
  - Header: check label + status pill (`1 erreur` / `2 avertissements` / `OK`)
  - Collapsed by default when OK; expanded when ERROR or WARNING
  - Expansion toggle: Lucide `chevron-down` / `chevron-up` icon, CSS-only via `<details>`/`<summary>`
  - Detail rows: `[p.1]` page badge, message text, key/value pairs in muted smaller font

## SVG Icon Fix

The current `_lucide_icon` bug: `LUCIDE_ICONS` is defined twice (lines 31 and 139 of `app.py`), and `_lucide_icon` is also defined twice (lines 38 and 145). The second definition only contains `search` and `info`, silently dropping `check_circle`, `alert_triangle`, `x_circle`.

**Fix:** Merge into a single `LUCIDE_ICONS` dict and single `_lucide_icon` function, defined once at the top of `app.py`. All icons used anywhere in the app (verdict, expand buttons, top bar, upload area) must be present in this dict. No emoji anywhere in the UI.

## Files to Change

| File | Change |
|---|---|
| `app.py` | Full rewrite of layout — remove sidebar, add top-bar controls, two-column results, fix icon bug |
| `preflight/report_html.py` | Update `build_html_report` to emit `<details>`/`<summary>` collapsible cards with colored left borders; use Lucide icons passed in as strings |

## Design Constraints

- No emoji anywhere — Lucide SVG icons only
- Stays Streamlit (no framework replacement)
- All business logic stays in `preflight/` — `app.py` is UI only
- Session state persistence behavior unchanged
- OCR expander stays available but moved to bottom of left panel
