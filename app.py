"""Getinside Print Preflight Checker — Streamlit UI."""

from __future__ import annotations

from html import escape

import streamlit as st

from preflight.document import Document, DocumentError, UploadedFile
from preflight.formats import FORMAT_NAMES, custom_format, get_format
from preflight.industries import INDUSTRY_NAMES
from preflight.pipeline import (
    CheckContext,
    ExtractionInfo,
    LOGO_LIBRARY_ROOT,
    overall_verdict,
    run_all_checks_with_extraction,
    summarize,
)
from preflight.checks import Severity
from preflight.logos import LogoLibrary
from preflight.metadata import extract_metadata, software_flag
from preflight.report_html import build_html_report

st.set_page_config(
    page_title="Print Preflight · Getinside",
    page_icon="🖨️",
    layout="wide",
)

LUCIDE_ICONS = {
    "check_circle": """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>""",
    "alert_triangle": """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>""",
    "x_circle": """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>""",
}


def _lucide_icon(name: str) -> str:
    return LUCIDE_ICONS.get(name, "")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, .stApp {
    font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
}

h1, h2, h3, h4 {
    font-size: 15px !important;
    font-weight: 600;
}

p, div, span {
    font-size: 13px;
}

.stMarkdown {
    font-size: 13px;
}

.stCaption {
    font-size: 11px !important;
}

pre, code, kbd {
    font-family: 'JetBrains Mono', ui-monospace, 'Cascadia Code', 'Fira Code', monospace;
    font-size: 11px;
    line-height: 1.5;
}
</style>""", unsafe_allow_html=True)

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
            chips.append(f"<span style='color:#374151'>PDF: {escape(meta.pdf_version)}</span>")
        if meta.pdf_x:
            chips.append(f"<span style='color:#16a34a;font-weight:600'>PDF/X: {escape(meta.pdf_x)}</span>")
        else:
            chips.append("<span style='color:#d97706;font-weight:600'>PDF/X: Non conforme</span>")
        software_name = meta.creator or meta.producer
        if software_name:
            color = "#d97706" if flag == "suspicious" else "#6b7280"
            prefix = "⚠️" if flag == "suspicious" else "Créé avec: "
            chips.append(f"<span style='color:{color};font-weight:{'600' if flag == 'suspicious' else 'normal'}'>{prefix}{escape(software_name)}</span>")
        if meta.creation_date:
            chips.append(f"<span style='color:#6b7280'>Créé le: {escape(meta.creation_date)}</span>")
    else:
        if meta.file_format:
            chips.append(f"<span style='color:#374151'>Format: {escape(meta.file_format)}</span>")
        if meta.color_mode:
            chips.append(f"<span style='color:#374151'>Couleur: {escape(meta.color_mode)}</span>")
        if meta.dpi:
            chips.append(f"<span style='color:#374151'>DPI: {escape(meta.dpi)}</span>")

    sep = "<span style='color:#d1d5db'>&nbsp;·&nbsp;</span>"
    meta_html = sep.join(chips) if chips else ""

    # QR URL
    if qr_url:
        short = qr_url if len(qr_url) <= 60 else qr_url[:57] + "…"
        url_html = f'<a href="{escape(qr_url)}" target="_blank" style="color:#2563eb;font-weight:600;text-decoration:none">QR: {escape(short)}</a>'
    else:
        url_html = "<span style='color:#9ca3af'>QR: Aucune URL détectée</span>"

    # Promo code
    if promo_code:
        promo_html = f"<span style='background:#dcfce7;color:#166534;font-weight:700;padding:2px 8px;border-radius:4px;font-size:12px'>Code: {escape(promo_code)}</span>"
    else:
        promo_html = "<span style='color:#9ca3af;font-size:12px'>Code: Aucun</span>"

    st.markdown(
        f"<div style='border:1px solid #e5e7eb;background:#f9fafb;border-radius:8px;"
        f"padding:10px 14px;margin-bottom:12px'>"
        f"<div style='font-size:13px;font-weight:600;color:#111827;margin-bottom:6px'>Fichier: {escape(doc_name)}</div>"
        f"<div style='display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:6px'>"
        f"{url_html}&nbsp;&nbsp;{promo_html}"
        f"</div>"
        f"<div style='font-size:11px;line-height:1.6;color:#6b7280'>{meta_html}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_html_report(results, context: CheckContext) -> None:
    st.markdown(build_html_report(results, context), unsafe_allow_html=True)


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
        results, extraction_info = run_all_checks_with_extraction(
            document, context, logo_library=library
        )

    st.session_state["results"] = results
    st.session_state["extraction_info"] = extraction_info
    st.session_state["context"] = context

    # 1. Preview at top, always visible, small thumbnails
    n_pages = len(document.pages)
    thumb_cols = st.columns(n_pages + (4 - n_pages))  # pad so thumbs stay narrow
    for col, page in zip(thumb_cols, document.pages):
        with col:
            st.caption(f"Page {page.index + 1} — {page.source.upper()}")
            try:
                preview = page.render(dpi=72) if page.source == "pdf" else page.render()
                st.image(preview, use_container_width=True)
                if st.button("🔍 Agrandir", key=f"view_page_{page.index}"):
                    st.session_state[f"show_page_{page.index}"] = True
            except Exception as exc:  # pragma: no cover
                st.caption(f"Aperçu indisponible : {exc}")

    # Handle full-size modal views (check all page indices)
    for page_idx in range(n_pages):
        if st.session_state.get(f"show_page_{page_idx}", False):
            with st.dialog(f"Page {page_idx + 1}"):
                try:
                    page = document.pages[page_idx]
                    full_img = page.render(dpi=300)
                    st.image(full_img, use_container_width=True)
                except Exception as exc:
                    st.error(f"Impossible d'afficher : {exc}")
                if st.button("Fermer", key=f"close_page_{page_idx}"):
                    st.session_state[f"show_page_{page_idx}"] = False
                    st.rerun()

    # 2. Key info banner (filename, URL, promo code, metadata)
    _render_key_info_banner(doc_name, results, document)

    # 3. Verdict summary
    counts = summarize(results)
    verdict = overall_verdict(results)
    e = counts.get("error", 0)
    w = counts.get("warning", 0)
    i = counts.get("info", 0)
    if verdict == "fail":
        bg = "#fee2e2"
        icon = _lucide_icon("x_circle")
        color = "#dc2626"
        main = f"{icon} <b>✕ {e} erreur{'s' if e > 1 else ''}</b>"
        if w:
            main += f" · ⚠️ {w} avertissement{'s' if w > 1 else ''}"
    elif verdict == "review":
        bg = "#fef3c7"
        icon = _lucide_icon("alert_triangle")
        color = "#92400e"
        main = f"{icon} <b>⚠️ {w} avertissement{'s' if w > 1 else ''}</b>"
    else:
        bg = "#dcfce7"
        icon = _lucide_icon("check_circle")
        color = "#166534"
        main = f"{icon} <b>✓ Conforme</b> — prêt pour l'impression"

    st.markdown(
        f"<div style='background:{bg};border-radius:8px;padding:12px 16px;margin-bottom:12px'>"
        f"<span style='color:{color};font-size:14px'>{main}</span>"
        f"<span style='color:#6b7280;font-size:13px'>  ·  ℹ️ {i} infos</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # 4. HTML report
    _render_html_report(results, context)

    st.divider()

    # 5. Debug section (discrete button + modal at bottom)
    if st.button("🔧 Détails OCR", key="debug_button", help="Afficher les détails techniques (OCR)"):
        st.session_state["show_debug"] = True

    if st.session_state.get("show_debug", False):
        ext_info = st.session_state.get("extraction_info")
        if ext_info:
            with st.dialog("🔧 Détails OCR"):
                st.markdown("**Paramètres OCR utilisés:**")
                st.markdown(f"- **DPI:** {ext_info.ocr_settings.dpi}")
                st.markdown(f"- **Langue:** {ext_info.ocr_settings.lang}")
                st.markdown(f"- **Config:** `{ext_info.ocr_settings.config}`")
                st.markdown(f"- **Prétraitement:** {', '.join(ext_info.ocr_settings.preprocessing)}")

                st.markdown("---")
                st.markdown("**Texte détecté par page:**")

                for pt in ext_info.pages:
                    st.markdown(f"**Page {pt.page_index + 1}** — Méthode: `{pt.method.value}`")
                    if pt.text.strip():
                        with st.container():
                            st.code(pt.text.strip()[:2000] + ("..." if len(pt.text.strip()) > 2000 else ""), language=None)
                    else:
                        st.caption("(aucun texte détecté)")

                st.markdown("---")
                st.markdown("**Texte complet concaténé:**")
                with st.container():
                    st.code(ext_info.text_used[:3000] + ("..." if len(ext_info.text_used) > 3000 else ""), language=None)

                if st.button("Fermer", key="close_debug"):
                    st.session_state["show_debug"] = False
                    st.rerun()
        else:
            st.warning("Aucune donnée d'extraction disponible.")

elif not uploaded:
    st.caption("📥 Déposez un PDF (1-2 pages) ou jusqu'à 2 images PNG/JPEG.")
