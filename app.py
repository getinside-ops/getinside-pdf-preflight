"""Getinside Print Preflight Checker — Streamlit UI."""

from __future__ import annotations

import streamlit as st

from preflight.document import Document, DocumentError, UploadedFile
from preflight.formats import FORMAT_NAMES, custom_format, get_format
from preflight.industries import INDUSTRY_NAMES
from preflight.pipeline import (
    CheckContext,
    LOGO_LIBRARY_ROOT,
    overall_verdict,
    run_all_checks,
    summarize,
)
from preflight.checks import Severity
from preflight.logos import LogoLibrary

st.set_page_config(
    page_title="Print Preflight · Getinside",
    page_icon="🖨️",
    layout="wide",
)

# ---------- Sidebar -----------------------------------------------------------

st.sidebar.markdown("**🖨️ Paramètres**")
st.sidebar.divider()

format_name = st.sidebar.selectbox("Format", options=FORMAT_NAMES, index=0)
if format_name == "Custom":
    custom_w = st.sidebar.number_input("Largeur (mm)", min_value=10, max_value=1000, value=148, step=1)
    custom_h = st.sidebar.number_input("Hauteur (mm)", min_value=10, max_value=1000, value=210, step=1)
    format_spec = custom_format(float(custom_w), float(custom_h))
else:
    format_spec = get_format(format_name)

industry = st.sidebar.selectbox("Industrie", options=INDUSTRY_NAMES)

print_method = st.sidebar.radio(
    "Impression",
    options=["Imprimé par getinside", "Imprimé par la marque"],
)

# ---------- Main panel --------------------------------------------------------

st.markdown("#### 🖨️ Print Preflight — Getinside")

uploaded = st.file_uploader(
    "PDF (1-2 pages) ou 1-2 images PNG/JPEG",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

run_button = st.button(
    "Lancer la vérification",
    type="primary",
    disabled=not uploaded,
)

# ---------- Check metadata (display order + labels) ---------------------------

_CHECK_META: dict[str, tuple[str, str]] = {
    "dimensions": ("📐", "Dimensions"),
    "colorspace":  ("🎨", "Couleurs"),
    "qrcode":      ("📱", "QR Code"),
    "logos":       ("🏷️", "Logos"),
    "advertiser":  ("🏢", "Annonceur"),
    "offer":       ("📅", "Offre"),
    "printer":     ("🖨️", "Imprimeur"),
    "industry":    ("⚖️", "Réglementaire"),
}
_CHECK_ORDER = list(_CHECK_META.keys())

_ROW_BORDER = {
    Severity.ERROR:   ("3px solid #ef4444", "#fef2f2", "#b91c1c"),
    Severity.WARNING: ("3px solid #f59e0b", "#fffbeb", "#92400e"),
    Severity.INFO:    ("1px solid #e5e7eb", "#fafafa",  "#374151"),
}

_SEVERITY_ICON = {
    Severity.ERROR:   "❌",
    Severity.WARNING: "⚠️",
    Severity.INFO:    "✓",
}


# ---------- Helpers -----------------------------------------------------------


def _fmt_val(v) -> str:
    """Format a detail dict value for human reading."""
    if isinstance(v, (list, tuple)):
        if len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
            return f"{v[0]:g} × {v[1]:g} mm"
        return ", ".join(str(x).strip("'\"") for x in v)
    if isinstance(v, str) and (v.startswith("http://") or v.startswith("https://")):
        short = v if len(v) <= 50 else v[:47] + "…"
        return f'<a href="{v}" target="_blank" style="color:#2563eb">{short}</a>'
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _detail_line(r) -> str:
    if not r.details:
        return ""
    skip = {"threshold", "kind", "expected_contains", "candidates"}
    parts = [
        f"<b style='color:#6b7280'>{k}</b>&nbsp;{_fmt_val(v)}"
        for k, v in r.details.items()
        if k not in skip
    ]
    if not parts:
        return ""
    return (
        "<div style='margin-top:4px;padding-top:4px;"
        "border-top:1px solid #e5e7eb;font-size:11.5px;color:#6b7280'>"
        + "&emsp;·&emsp;".join(parts)
        + "</div>"
    )


def _render_row(r) -> str:
    border, bg, text_color = _ROW_BORDER[r.severity]
    icon = _SEVERITY_ICON[r.severity]
    page_span = (
        f"<span style='font-size:11px;color:#9ca3af;margin-left:4px'>"
        f"Page&nbsp;{r.page + 1}</span>"
        if r.page is not None else ""
    )
    return (
        f"<div style='border-left:{border};background:{bg};"
        f"padding:8px 14px;margin:4px 0;border-radius:0 8px 8px 0'>"
        f"<div style='display:flex;align-items:baseline;gap:6px'>"
        f"<span>{icon}{page_span}</span>"
        f"<span style='font-size:13.5px;color:{text_color}'>{r.message}</span>"
        f"</div>"
        f"{_detail_line(r)}"
        f"</div>"
    )


def _group_worst(items) -> Severity:
    if any(r.severity is Severity.ERROR for r in items):
        return Severity.ERROR
    if any(r.severity is Severity.WARNING for r in items):
        return Severity.WARNING
    return Severity.INFO


def _verdict_banner(verdict: str, counts: dict) -> None:
    e = counts.get("error", 0)
    w = counts.get("warning", 0)
    i = counts.get("info", 0)
    if verdict == "fail":
        parts = [f"❌ **{e} erreur{'s' if e > 1 else ''}**"]
        if w:
            parts.append(f"⚠️ {w} avertissement{'s' if w > 1 else ''}")
        st.error("  ·  ".join(parts) + f"  ·  ℹ️ {i} infos")
    elif verdict == "review":
        st.warning(f"⚠️ **{w} avertissement{'s' if w > 1 else ''}**  ·  ℹ️ {i} infos")
    else:
        st.success(f"✅ **Conforme** — prêt pour l'impression  ·  ℹ️ {i} infos")


def _render_results(results) -> None:
    counts = summarize(results)
    verdict = overall_verdict(results)
    _verdict_banner(verdict, counts)
    st.write("")

    # Group by check name, preserving defined order
    groups: dict[str, list] = {}
    for r in results:
        groups.setdefault(r.check_name, []).append(r)

    ordered_keys = (
        [k for k in _CHECK_ORDER if k in groups]
        + [k for k in groups if k not in _CHECK_ORDER]
    )

    _SECTION_BG = {
        Severity.ERROR:   "#fff5f5",
        Severity.WARNING: "#fffdf0",
        Severity.INFO:    "#f9fafb",
    }
    _SECTION_BORDER = {
        Severity.ERROR:   "#fca5a5",
        Severity.WARNING: "#fcd34d",
        Severity.INFO:    "#e5e7eb",
    }

    for name in ordered_keys:
        items = groups[name]
        worst = _group_worst(items)
        icon, label = _CHECK_META.get(name, ("•", name.title()))

        e_count = sum(1 for r in items if r.severity is Severity.ERROR)
        w_count = sum(1 for r in items if r.severity is Severity.WARNING)

        if worst is Severity.ERROR:
            status_html = f"<span style='color:#dc2626;font-weight:600'>❌ {e_count} erreur{'s' if e_count > 1 else ''}</span>"
        elif worst is Severity.WARNING:
            status_html = f"<span style='color:#d97706;font-weight:600'>⚠️ {w_count} avertissement{'s' if w_count > 1 else ''}</span>"
        else:
            status_html = "<span style='color:#16a34a;font-weight:600'>✅</span>"

        bg = _SECTION_BG[worst]
        border = _SECTION_BORDER[worst]
        rows_html = "".join(_render_row(r) for r in items)

        st.markdown(
            f"<div style='border:1px solid {border};background:{bg};"
            f"border-radius:10px;padding:10px 14px;margin-bottom:10px'>"
            f"<div style='font-size:13px;font-weight:600;color:#374151;margin-bottom:6px'>"
            f"{icon} {label} &nbsp;{status_html}</div>"
            f"{rows_html}"
            f"</div>",
            unsafe_allow_html=True,
        )


# ---------- Run ---------------------------------------------------------------

if run_button and uploaded:
    files = [UploadedFile(name=u.name, data=u.read()) for u in uploaded]
    try:
        document = Document.from_upload(files)
    except DocumentError as exc:
        st.error(str(exc))
        st.stop()

    context = CheckContext(
        format_spec=format_spec,
        industry=industry,
        print_method=print_method,
    )

    library = LogoLibrary(LOGO_LIBRARY_ROOT)

    with st.spinner("Analyse en cours…"):
        results = run_all_checks(document, context, logo_library=library)

    _render_results(results)

    with st.expander("Aperçu des pages", expanded=False):
        cols = st.columns(max(len(document.pages), 1))
        for col, page in zip(cols, document.pages):
            with col:
                st.caption(f"Page {page.index + 1} — {page.source.upper()}")
                try:
                    preview = page.render(dpi=120) if page.source == "pdf" else page.render()
                    st.image(preview, use_container_width=True)
                except Exception as exc:  # pragma: no cover
                    st.caption(f"Aperçu indisponible : {exc}")

elif not uploaded:
    st.caption("📥 Déposez un PDF (1-2 pages) ou jusqu'à 2 images PNG/JPEG.")
