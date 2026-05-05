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

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

div[data-testid="stVerticalBlock"]:has(> div > div > img):has(~ div > button) {
    position: relative;
}

div[data-testid="stVerticalBlock"]:has(> div > div > img):has(~ div > button) button {
    position: absolute !important;
    top: 8px !important;
    right: 8px !important;
    z-index: 999 !important;
    background: rgba(255,255,255,0.95) !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    padding: 8px !important;
    min-width: 40px !important;
    min-height: 40px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
    opacity: 0.85 !important;
    transition: opacity 0.2s, box-shadow 0.2s !important;
}

div[data-testid="stVerticalBlock"]:has(> div > div > img):has(~ div > button) button:hover {
    opacity: 1 !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
    background: rgba(255,255,255,1) !important;
}

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

    sections: list[str] = []

    # Section: Fichier
    file_items = [f"📄 {escape(doc_name)}", f"📊 {document.page_count} page{'s' if document.page_count > 1 else ''}"]
    sections.append(f"<div><span style='color:#6b7280;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px'>Fichier</span><div style='font-size:13px;color:#111827;margin-top:4px'>{' · '.join(file_items)}</div></div>")

    # Section: QR Code
    if qr_url:
        short = qr_url if len(qr_url) <= 50 else qr_url[:47] + "…"
        qr_section = f"<a href='{escape(qr_url)}' target='_blank' style='color:#2563eb;text-decoration:none;font-weight:500'>{escape(short)} ↗</a>"
    else:
        qr_section = "<span style='color:#9ca3af'>Non détecté</span>"
    sections.append(f"<div><span style='color:#6b7280;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px'>QR Code</span><div style='font-size:13px;margin-top:4px'>{qr_section}</div></div>")

    # Section: Code promo
    if promo_code:
        promo_section = f"<span style='background:#dcfce7;color:#166534;font-weight:600;padding:2px 8px;border-radius:4px;font-size:12px'>{escape(promo_code)}</span>"
    else:
        promo_section = "<span style='color:#9ca3af'>Non détecté</span>"
    sections.append(f"<div><span style='color:#6b7280;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px'>Code Promo</span><div style='font-size:13px;margin-top:4px'>{promo_section}</div></div>")

    # Section: Métadonnées PDF/Image
    if document.kind == "pdf":
        meta_parts = []
        
        # PDF version and PDF/X
        if meta.pdf_version:
            meta_parts.append(f"PDF v{meta.pdf_version}")
        if meta.pdf_x:
            pdfx_color = "#16a34a" if meta.pdf_x else "#d97706"
            pdfx_text = meta.pdf_x if meta.pdf_x else "Non conforme"
            meta_parts.append(f"<span style='color:{pdfx_color};font-weight:600'>{pdfx_text}</span>")
        elif meta.pdf_version:
            meta_parts.append(f"<span style='color:#d97706'>PDF/X: Non conforme</span>")
        
        # Software with warning
        software = meta.creator or meta.producer
        if software:
            warn_color = "#d97706" if flag == "suspicious" else "#6b7280"
            warn_icon = "⚠️" if flag == "suspicious" else ""
            meta_parts.append(f"<span style='color:{warn_color}'>{warn_icon} {escape(software)}</span>")
        
        # Dates
        if meta.creation_date:
            meta_parts.append(f"Créé: {escape(meta.creation_date)}")
        if meta.mod_date:
            meta_parts.append(f"Modifié: {escape(meta.mod_date)}")

        meta_section = " · ".join(meta_parts) if meta_parts else "<span style='color:#9ca3af'>Aucune</span>"
        sections.append(f"<div><span style='color:#6b7280;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px'>Métadonnées</span><div style='font-size:12px;color:#374151;margin-top:4px'>{meta_section}</div></div>")
    else:
        meta_items = []
        if meta.file_format:
            meta_items.append(escape(meta.file_format))
        if meta.color_mode:
            meta_items.append(escape(meta.color_mode))
        if meta.dpi:
            meta_items.append(f"{meta.dpi} DPI")

        meta_section = " · ".join(meta_items) if meta_items else "<span style='color:#9ca3af'>Aucune</span>"
        sections.append(f"<div><span style='color:#6b7280;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px'>Image</span><div style='font-size:12px;color:#374151;margin-top:4px'>{meta_section}</div></div>")

    grid_cols = "grid-template-columns: repeat(4, 1fr)" if len(sections) == 4 else "grid-template-columns: repeat(2, 1fr)"
    st.markdown(
        f"<div style='border:1px solid #e5e7eb;background:#ffffff;border-radius:12px;padding:16px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.05)'>"
        f"<div style='display:grid;gap:16px;{grid_cols};flex-wrap:wrap'>"
        + "".join(f"<div style='padding:8px 12px;background:#f9fafb;border-radius:8px;border:1px solid #f3f4f6'>{s}</div>" for s in sections)
        + f"</div></div>",
        unsafe_allow_html=True,
    )


def _render_html_report(results, context: CheckContext) -> None:
    st.markdown(build_html_report(results, context), unsafe_allow_html=True)


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


# ---------- Run ---------------------------------------------------------------

# Initialize variables for display code
display_results = False
document = None
results = None
extraction_info = None
context = None
doc_name = None

# Run analysis on button click OR restore from session state
if run_button and uploaded:
    # Read file data BEFORE storing in session (consumes the BytesIO)
    file_data = [(u.name, u.read()) for u in uploaded]
    doc_name = uploaded[0].name

    files = [UploadedFile(name=n, data=d) for n, d in file_data]

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
    st.session_state["doc_name"] = doc_name
    st.session_state["doc_data"] = file_data  # Already read, store for restoration
    display_results = True

elif has_stored_results and has_doc_data:
    # Restore from session state instead of using depleted uploaded files
    files = [UploadedFile(name=n, data=d) for n, d in st.session_state["doc_data"]]
    doc_name = st.session_state["doc_name"]
    try:
        document = Document.from_upload(files)
    except DocumentError as exc:
        st.error(str(exc))
        st.session_state.clear()
        st.rerun()

    results = st.session_state["results"]
    context = st.session_state["context"]
    extraction_info = st.session_state.get("extraction_info")
    display_results = True

# Display results if analysis was run (either now or from session state)
if display_results and document is not None:
    _display_analysis_results(document, results, context, extraction_info, doc_name)

elif not uploaded and not has_stored_results:
    st.caption("Déposez un PDF (1-2 pages) ou jusqu'à 2 images PNG/JPEG.")
