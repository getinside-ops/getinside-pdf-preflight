"""Pure HTML report builder — no Streamlit dependency."""
from __future__ import annotations

from html import escape

from preflight.checks import CheckResult, Severity
from preflight.pipeline import CheckContext

_CHECK_META: dict[str, tuple[str, str]] = {
    "dimensions": ("", "DIMENSIONS"),
    "bleed": ("", "FOND PERDU"),
    "colorspace":  ("", "COULEURS"),
    "transparency": ("", "TRANSPARENCE"),
    "image_resolution": ("", "RÉSOLUTION"),
    "qrcode":      ("", "QR CODE"),
    "logos":       ("", "LOGOS"),
    "advertiser":  ("", "ANNONCEUR"),
    "offer":       ("", "OFFRE"),
    "printer":     ("", "IMPRIMEUR"),
    "contrast":    ("", "CONTRASTE"),
    "industry":    ("", "RÉGLEMENTAIRE"),
    "font_embedding": ("", "POLICES"),
    "linked_images": ("", "IMAGES"),
    "spot_colors": ("", "COULEURS SPOT"),
    "page_boxes":  ("", "PAGE BOXES"),
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


def _format_message(r: CheckResult) -> str:
    """Format message, including key details inline instead of in brackets."""
    msg = r.message
    
    # Add QR code size inline
    if r.check_name == "qrcode" and r.details and "size_mm" in r.details:
        size = r.details["size_mm"]
        if size:
            msg += f" ({size[0]:.1f} × {size[1]:.1f} mm)"
    
    return msg


def build_html_report(results: list[CheckResult], context: CheckContext) -> str:
    """Return a self-contained HTML string for the preflight report."""
    header = escape(
        f"Format : {context.format_spec.name}"
        f"  ·  Industrie : {context.industry}"
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
            status = f"[ERROR] {e_count} erreur{'s' if e_count > 1 else ''}"
        elif worst is Severity.WARNING:
            status = f"[WARNING] {w_count} avertissement{'s' if w_count > 1 else ''}"
        else:
            status = "[OK]"

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
                f"<div style='padding-left:16px;font-size:12.5px;line-height:1.6'>"
                f"<span style='color:{dot_color}'>·</span> "
                f"{page_badge}"
                f"<span style='color:{text_color}'>{escape(formatted_msg)}</span>"
                f"</div>"
                f"{detail_lines}"
            )

        parts.append("</div>")

    parts.append("</div>")
    return "\n".join(parts)
