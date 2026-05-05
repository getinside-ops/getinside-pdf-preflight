# Rapport HTML structuré — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer `st.code()` par un rapport HTML structuré utilisant Inter, couleurs de sévérité et retour à la ligne automatique.

**Architecture:** La logique HTML est extraite dans `preflight/report_html.py` (fonction pure `build_html_report`), testable sans Streamlit. `app.py` garde uniquement un wrapper `_render_html_report` qui appelle `st.markdown`. Les helpers `_build_text_report`, `_meta_plain`, `_CHECK_META`, `_CHECK_ORDER`, `_group_worst`, `_detail_text`, `_fmt_detail_value`, `_SEVERITY_ICON` migrent dans le nouveau module ou sont supprimés.

**Tech Stack:** Python 3.13, Streamlit, pytest, `html.escape`

---

## File map

| Fichier | Action | Rôle |
|---|---|---|
| `preflight/report_html.py` | Créer | Fonction pure `build_html_report` + helpers |
| `tests/test_report_html.py` | Créer | Tests de `build_html_report` |
| `app.py` | Modifier | Supprimer ancien code, ajouter `_render_html_report` |

---

## Task 1 — Tests échouants pour `build_html_report`

**Files:**
- Create: `tests/test_report_html.py`

- [ ] **Step 1.1 — Écrire les tests**

Créer `tests/test_report_html.py` avec ce contenu exact :

```python
"""Tests for preflight.report_html.build_html_report."""
import pytest
from preflight.checks import CheckResult, Severity
from preflight.pipeline import CheckContext
from preflight.formats import get_format
from preflight.report_html import build_html_report


@pytest.fixture
def ctx():
    return CheckContext(
        format_spec=get_format("A5"),
        industry="Général",
        print_method="Imprimé par getinside",
    )


def _r(check_name, severity, message, page=None, details=None):
    return CheckResult(
        check_name=check_name,
        severity=severity,
        message=message,
        page=page,
        details=details or {},
    )


def test_header_contains_context(ctx):
    html = build_html_report([], ctx)
    assert "A5" in html
    assert "Général" in html
    assert "Imprimé par getinside" in html


def test_error_result_uses_red(ctx):
    results = [_r("dimensions", Severity.ERROR, "Taille incorrecte")]
    html = build_html_report(results, ctx)
    assert "#dc2626" in html
    assert "Taille incorrecte" in html


def test_warning_result_uses_orange(ctx):
    results = [_r("colorspace", Severity.WARNING, "Couleur non CMJN")]
    html = build_html_report(results, ctx)
    assert "#92400e" in html
    assert "Couleur non CMJN" in html


def test_info_result_uses_gray(ctx):
    results = [_r("logos", Severity.INFO, "Logo détecté")]
    html = build_html_report(results, ctx)
    assert "#6b7280" in html
    assert "Logo détecté" in html


def test_page_number_rendered(ctx):
    results = [_r("dimensions", Severity.ERROR, "Mauvaise taille", page=0)]
    html = build_html_report(results, ctx)
    assert "[p.1]" in html


def test_no_page_number_when_none(ctx):
    results = [_r("dimensions", Severity.ERROR, "Mauvaise taille", page=None)]
    html = build_html_report(results, ctx)
    assert "[p." not in html


def test_detail_text_rendered(ctx):
    results = [_r("dimensions", Severity.ERROR, "Taille", details={"found": [210.0, 297.0]})]
    html = build_html_report(results, ctx)
    # detail appears and is colored gray
    assert "#9ca3af" in html
    assert "210" in html


def test_check_order_respected(ctx):
    # dimensions comes before colorspace in _CHECK_ORDER
    results = [
        _r("colorspace", Severity.INFO, "OK"),
        _r("dimensions", Severity.ERROR, "Erreur"),
    ]
    html = build_html_report(results, ctx)
    assert html.index("DIMENSIONS") < html.index("COULEURS")


def test_unknown_check_fallback(ctx):
    results = [_r("custom_check", Severity.INFO, "Info")]
    html = build_html_report(results, ctx)
    assert "CUSTOM_CHECK" in html


def test_html_escaping(ctx):
    results = [_r("dimensions", Severity.ERROR, "<script>alert(1)</script>")]
    html = build_html_report(results, ctx)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
```

- [ ] **Step 1.2 — Vérifier que les tests échouent**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight" && source .venv/bin/activate && .venv/bin/pytest tests/test_report_html.py -v
```

Résultat attendu : `ModuleNotFoundError: No module named 'preflight.report_html'`

---

## Task 2 — Implémenter `preflight/report_html.py`

**Files:**
- Create: `preflight/report_html.py`

- [ ] **Step 2.1 — Créer le module**

Créer `preflight/report_html.py` avec ce contenu exact :

```python
"""Pure HTML report builder — no Streamlit dependency."""
from __future__ import annotations

from html import escape

from preflight.checks import CheckResult, Severity
from preflight.pipeline import CheckContext

_CHECK_META: dict[str, tuple[str, str]] = {
    "dimensions": ("📐", "DIMENSIONS"),
    "colorspace":  ("🎨", "COULEURS"),
    "qrcode":      ("📱", "QR CODE"),
    "logos":       ("🏷️", "LOGOS"),
    "advertiser":  ("🏢", "ANNONCEUR"),
    "offer":       ("📅", "OFFRE"),
    "printer":     ("🖨️", "IMPRIMEUR"),
    "industry":    ("⚖️", "RÉGLEMENTAIRE"),
}
_CHECK_ORDER = list(_CHECK_META.keys())

_SEV_COLORS: dict[Severity, tuple[str, str]] = {
    Severity.ERROR:   ("#dc2626", "#dc2626"),
    Severity.WARNING: ("#92400e", "#d97706"),
    Severity.INFO:    ("#6b7280", "#9ca3af"),
}


def _group_worst(items: list[CheckResult]) -> Severity:
    if any(r.severity is Severity.ERROR for r in items):
        return Severity.ERROR
    if any(r.severity is Severity.WARNING for r in items):
        return Severity.WARNING
    return Severity.INFO


def _fmt_detail_value(v: object) -> str:
    if isinstance(v, (list, tuple)):
        if len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
            return f"{v[0]:g} × {v[1]:g} mm"
        return ", ".join(str(x).strip("'\"") for x in v)
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _detail_text(r: CheckResult) -> str:
    if not r.details:
        return ""
    skip = {"threshold", "kind", "expected_contains", "candidates", "data", "code", "date"}
    parts = [
        f"{k}: {_fmt_detail_value(v)}"
        for k, v in r.details.items()
        if k not in skip
    ]
    return "  [" + " · ".join(parts) + "]" if parts else ""


def build_html_report(results: list[CheckResult], context: CheckContext) -> str:
    """Return a self-contained HTML string for the preflight report."""
    header = escape(
        f"Format : {context.format_spec.name}"
        f"  ·  Industrie : {context.industry}"
        f"  ·  {context.print_method}"
    )

    parts: list[str] = [
        "<div style='border:1px solid #e5e7eb;background:#f9fafb;border-radius:8px;"
        "padding:10px 14px;margin-bottom:8px;"
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

    for i, name in enumerate(ordered_keys):
        items = groups[name]
        worst = _group_worst(items)
        icon, label = _CHECK_META.get(name, ("•", name.upper()))

        e_count = sum(1 for r in items if r.severity is Severity.ERROR)
        w_count = sum(1 for r in items if r.severity is Severity.WARNING)

        if worst is Severity.ERROR:
            status = f"❌ {e_count} erreur{'s' if e_count > 1 else ''}"
        elif worst is Severity.WARNING:
            status = f"⚠️ {w_count} avertissement{'s' if w_count > 1 else ''}"
        else:
            status = "✅"

        mt = "margin-top:10px;border-top:1px solid #f3f4f6;padding-top:10px" if i > 0 else ""
        parts.append(
            f"<div style='{mt}'>"
            f"<div style='font-size:13px;font-weight:600;color:#111827;margin-bottom:4px'>"
            f"{icon} {escape(label)} — {status}</div>"
        )

        for r in items:
            text_color, dot_color = _SEV_COLORS[r.severity]
            page_badge = ""
            if r.page is not None:
                page_badge = (
                    f"<span style='background:#f3f4f6;color:#6b7280;font-size:11px;"
                    f"padding:1px 5px;border-radius:3px;margin-right:4px'>[p.{r.page + 1}]</span>"
                )
            detail = _detail_text(r)
            detail_html = (
                f" <span style='color:#9ca3af'>{escape(detail)}</span>" if detail else ""
            )
            parts.append(
                f"<div style='padding-left:16px;font-size:12.5px;line-height:1.6'>"
                f"<span style='color:{dot_color}'>·</span> "
                f"{page_badge}"
                f"<span style='color:{text_color}'>{escape(r.message)}</span>"
                f"{detail_html}</div>"
            )

        parts.append("</div>")

    parts.append("</div>")
    return "\n".join(parts)
```

- [ ] **Step 2.2 — Faire passer les tests**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight" && .venv/bin/pytest tests/test_report_html.py -v
```

Résultat attendu : tous les tests `PASSED`.

- [ ] **Step 2.3 — Vérifier que la suite complète passe toujours**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight" && .venv/bin/pytest -q
```

Résultat attendu : suite complète verte (OCR-dependent tests éventuellement skippés).

- [ ] **Step 2.4 — Committer**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight" && rtk git add preflight/report_html.py tests/test_report_html.py && rtk git commit -m "feat: add build_html_report pure function with tests"
```

---

## Task 3 — Mettre à jour `app.py`

**Files:**
- Modify: `app.py`

- [ ] **Step 3.1 — Supprimer les fonctions obsolètes et l'import inutilisé**

Dans `app.py`, supprimer en entier :
- Le dict `_CHECK_META`
- La liste `_CHECK_ORDER`
- Le dict `_SEVERITY_ICON`
- La fonction `_fmt_detail_value`
- La fonction `_detail_text`
- La fonction `_group_worst` (elle migre dans `preflight/report_html.py`)
- La fonction `_build_text_report`
- La fonction `_meta_plain`

Conserver : `_extract_qr_url`, `_extract_promo_code`, `_render_key_info_banner`.

- [ ] **Step 3.2 — Ajouter l'import et le wrapper**

En haut de `app.py`, ajouter l'import après les imports existants de `preflight/` :

```python
from preflight.report_html import build_html_report
```

Après la fonction `_render_key_info_banner`, ajouter :

```python
def _render_html_report(results, context: CheckContext) -> None:
    st.markdown(build_html_report(results, context), unsafe_allow_html=True)
```

- [ ] **Step 3.3 — Mettre à jour le bloc `run_button`**

Dans le bloc `if run_button and uploaded:`, remplacer les 3 lignes :

```python
    # 4. Single copyable text report
    meta_str = _meta_plain(document)
    report = _build_text_report(results, doc_name, context, meta_str)
    st.code(report, language=None)
```

Par :

```python
    # 4. HTML report
    _render_html_report(results, context)
```

- [ ] **Step 3.4 — Vérifier que la suite de tests passe**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight" && .venv/bin/pytest -q
```

Résultat attendu : suite complète verte.

- [ ] **Step 3.5 — Committer**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight" && rtk git add app.py && rtk git commit -m "feat: replace st.code report with structured HTML using Inter font"
```
