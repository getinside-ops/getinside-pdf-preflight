"""Getinside Print Preflight Checker — Streamlit UI."""

from __future__ import annotations

from html import escape

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
from preflight.metadata import extract_metadata, software_flag

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

_SEVERITY_ICON = {
    Severity.ERROR:   "❌",
    Severity.WARNING: "⚠️",
    Severity.INFO:    "✓",
}


# ---------- Helpers -----------------------------------------------------------


def _extract_qr_url(results) -> str | None:
    for r in results:
        if r.check_name == "qrcode" and r.details and "data" in r.details:
            return r.details["data"]
    return None


def _extract_promo_code(results) -> str | None:
    for r in results:
        if r.check_name == "offer" and r.details and "code" in r.details:
            return r.details["code"]
    return None


def _group_worst(items) -> Severity:
    if any(r.severity is Severity.ERROR for r in items):
        return Severity.ERROR
    if any(r.severity is Severity.WARNING for r in items):
        return Severity.WARNING
    return Severity.INFO


def _fmt_detail_value(v) -> str:
    if isinstance(v, (list, tuple)):
        if len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
            return f"{v[0]:g} × {v[1]:g} mm"
        return ", ".join(str(x).strip("'\"") for x in v)
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _detail_text(r) -> str:
    if not r.details:
        return ""
    skip = {"threshold", "kind", "expected_contains", "candidates", "data", "code", "date"}
    parts = [
        f"{k}: {_fmt_detail_value(v)}"
        for k, v in r.details.items()
        if k not in skip
    ]
    return "  [" + " · ".join(parts) + "]" if parts else ""


def _build_text_report(
    results,
    doc_name: str,
    context: CheckContext,
    meta_str: str,
) -> str:
    counts = summarize(results)
    verdict = overall_verdict(results)
    e = counts.get("error", 0)
    w = counts.get("warning", 0)
    i = counts.get("info", 0)

    qr_url = _extract_qr_url(results)
    promo_code = _extract_promo_code(results)

    lines: list[str] = []

    # Header
    lines.append("=" * 56)
    lines.append(f"  PREFLIGHT — {doc_name}")
    lines.append(f"  Format: {context.format_spec.name}  ·  Industrie: {context.industry}  ·  {context.print_method}")
    if meta_str:
        lines.append(f"  {meta_str}")
    lines.append("=" * 56)
    lines.append("")

    # Verdict
    if verdict == "fail":
        v_parts = [f"❌ {e} erreur{'s' if e > 1 else ''}"]
        if w:
            v_parts.append(f"⚠️ {w} avertissement{'s' if w > 1 else ''}")
        v_parts.append(f"ℹ️ {i} infos")
        lines.append("  RÉSULTAT : " + "  ·  ".join(v_parts))
    elif verdict == "review":
        lines.append(f"  RÉSULTAT : ⚠️ {w} avertissement{'s' if w > 1 else ''}  ·  ℹ️ {i} infos")
    else:
        lines.append(f"  RÉSULTAT : ✅ Conforme — prêt pour l'impression  ·  ℹ️ {i} infos")

    lines.append("")

    # Key campaign info
    if qr_url:
        lines.append(f"  🔗 URL QR   : {qr_url}")
    if promo_code:
        lines.append(f"  🎟️  Code promo : {promo_code}  ✅")
    else:
        lines.append(f"  🎟️  Code promo : (aucun détecté)")

    lines.append("")
    lines.append("-" * 56)

    # Group results by check
    groups: dict[str, list] = {}
    for r in results:
        groups.setdefault(r.check_name, []).append(r)

    ordered_keys = (
        [k for k in _CHECK_ORDER if k in groups]
        + [k for k in groups if k not in _CHECK_ORDER]
    )

    for name in ordered_keys:
        items = groups[name]
        worst = _group_worst(items)
        icon, label = _CHECK_META.get(name, ("•", name.upper()))

        e_count = sum(1 for r in items if r.severity is Severity.ERROR)
        w_count = sum(1 for r in items if r.severity is Severity.WARNING)

        if worst is Severity.ERROR:
            status = f"❌ {e_count} erreur{'s' if e_count > 1 else ''}"
        elif worst is Severity.WARNING:
            status = f"⚠️  {w_count} avertissement{'s' if w_count > 1 else ''}"
        else:
            status = "✅"

        lines.append("")
        lines.append(f"{icon} {label} — {status}")

        for r in items:
            sev_icon = _SEVERITY_ICON[r.severity]
            page_tag = f" [p.{r.page + 1}]" if r.page is not None else ""
            detail = _detail_text(r)
            lines.append(f"  {sev_icon}{page_tag} {r.message}{detail}")

    lines.append("")
    lines.append("=" * 56)

    return "\n".join(lines)


def _meta_plain(document: Document) -> str:
    """Return a short one-line metadata string for the text report."""
    meta = extract_metadata(document)
    parts: list[str] = []
    if document.kind == "pdf":
        if meta.pdf_version:
            parts.append(meta.pdf_version)
        if meta.pdf_x:
            parts.append(meta.pdf_x)
        else:
            parts.append("Non PDF/X")
        software_name = meta.creator or meta.producer
        if software_name:
            parts.append(software_name)
        if meta.creation_date:
            parts.append(meta.creation_date)
    else:
        if meta.file_format:
            parts.append(meta.file_format)
        if meta.color_mode:
            parts.append(meta.color_mode)
        if meta.dpi:
            parts.append(f"{meta.dpi} DPI")
    return "  ·  ".join(parts)


def _render_key_info_banner(doc_name: str, results, document: Document) -> None:
    """Render the prominent key-info header above the report."""
    meta = extract_metadata(document)
    flag = software_flag(meta)
    qr_url = _extract_qr_url(results)
    promo_code = _extract_promo_code(results)

    # Build metadata chips
    chips: list[str] = []
    if document.kind == "pdf":
        if meta.pdf_version:
            chips.append(f"<span style='color:#374151'>📄 {escape(meta.pdf_version)}</span>")
        if meta.pdf_x:
            chips.append(f"<span style='color:#16a34a;font-weight:600'>✅ {escape(meta.pdf_x)}</span>")
        else:
            chips.append("<span style='color:#d97706;font-weight:600'>⚠️ Non PDF/X</span>")
        software_name = meta.creator or meta.producer
        if software_name:
            color = "#d97706" if flag == "suspicious" else "#6b7280"
            prefix = "⚠️" if flag == "suspicious" else "✏️"
            chips.append(f"<span style='color:{color};font-weight:{'600' if flag == 'suspicious' else 'normal'}'>{prefix} {escape(software_name)}</span>")
        if meta.creation_date:
            chips.append(f"<span style='color:#6b7280'>📅 {escape(meta.creation_date)}</span>")
    else:
        if meta.file_format:
            chips.append(f"<span style='color:#374151'>📄 {escape(meta.file_format)}</span>")
        if meta.color_mode:
            chips.append(f"<span style='color:#374151'>🎨 {escape(meta.color_mode)}</span>")
        if meta.dpi:
            chips.append(f"<span style='color:#374151'>🖨️ {escape(meta.dpi)} DPI</span>")

    sep = "<span style='color:#d1d5db'>&nbsp;·&nbsp;</span>"
    meta_html = sep.join(chips) if chips else ""

    # QR URL
    if qr_url:
        short = qr_url if len(qr_url) <= 60 else qr_url[:57] + "…"
        url_html = f'<a href="{escape(qr_url)}" target="_blank" style="color:#2563eb;font-weight:600;text-decoration:none">🔗 {escape(short)}</a>'
    else:
        url_html = "<span style='color:#9ca3af'>🔗 Aucune URL QR détectée</span>"

    # Promo code
    if promo_code:
        promo_html = f"<span style='background:#dcfce7;color:#166534;font-weight:700;padding:2px 8px;border-radius:4px;font-size:13px'>🎟️ {escape(promo_code)}</span>"
    else:
        promo_html = "<span style='color:#9ca3af;font-size:12px'>🎟️ Aucun code promo</span>"

    st.markdown(
        f"<div style='border:1px solid #e5e7eb;background:#f9fafb;border-radius:10px;"
        f"padding:12px 16px;margin-bottom:12px'>"
        f"<div style='font-size:15px;font-weight:700;color:#111827;margin-bottom:6px'>📄 {escape(doc_name)}</div>"
        f"<div style='display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:6px'>"
        f"{url_html}&nbsp;&nbsp;{promo_html}"
        f"</div>"
        f"<div style='font-size:11.5px;line-height:1.8'>{meta_html}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ---------- Run ---------------------------------------------------------------

if run_button and uploaded:
    files = [UploadedFile(name=u.name, data=u.read()) for u in uploaded]
    doc_name = uploaded[0].name

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

    # 1. Preview at top, always visible, small thumbnails
    n_pages = len(document.pages)
    thumb_cols = st.columns(n_pages + (4 - n_pages))  # pad so thumbs stay narrow
    for col, page in zip(thumb_cols, document.pages):
        with col:
            st.caption(f"Page {page.index + 1} — {page.source.upper()}")
            try:
                preview = page.render(dpi=72) if page.source == "pdf" else page.render()
                st.image(preview, use_container_width=True)
            except Exception as exc:  # pragma: no cover
                st.caption(f"Aperçu indisponible : {exc}")

    # 2. Key info banner (filename, URL, promo code, metadata)
    _render_key_info_banner(doc_name, results, document)

    # 3. Verdict summary
    counts = summarize(results)
    verdict = overall_verdict(results)
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

    # 4. Single copyable text report
    meta_str = _meta_plain(document)
    report = _build_text_report(results, doc_name, context, meta_str)
    st.code(report, language=None)

elif not uploaded:
    st.caption("📥 Déposez un PDF (1-2 pages) ou jusqu'à 2 images PNG/JPEG.")
