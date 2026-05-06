"""End-to-end pipeline integration test.

Builds a synthetic compliant A5 PDF (text + embedded QR) and runs the
full pipeline; expects no ERROR-level results except for the logo
check (the bundled phash library doesn't include the synthetic text-
generated content).
"""

from __future__ import annotations

import io

import fitz
import segno

from preflight.checks import Severity
from preflight.checks.printer import GETINSIDE_PRINTER_MENTION
from preflight.document import Document, UploadedFile
from preflight.formats import get_format
from preflight.logos import LogoLibrary
from preflight.pipeline import CheckContext, overall_verdict, run_all_checks
from tests.conftest import A5_H_PT, A5_W_PT


COMPLIANT_BODY = (
    "Getinside SAS — Capital social 50 000 euros. "
    "Siège social: 12 rue de l'Exemple, 75001 Paris. "
    "RCS Paris 123 456 789. "
    "Offre valable jusqu'au 31/12/2026. "
    "Code promo : HELLO2026. "
    + GETINSIDE_PRINTER_MENTION
    + "."
)


def _compliant_pdf(text_body: str = COMPLIANT_BODY) -> bytes:
    qr = segno.make("https://gtinsi.de/HELLO2026", error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=10, border=1)
    qr_bytes = buf.getvalue()

    doc = fitz.open()
    page = doc.new_page(width=A5_W_PT, height=A5_H_PT)
    # Text in upper area
    y = 60
    for line in text_body.split(". "):
        line = line.strip()
        if line:
            page.insert_text((40, y), line + ".", fontsize=9)
            y += 12
    # Sufficiently large QR (~28 mm)
    page.insert_image(fitz.Rect(40, 400, 40 + 80, 400 + 80), stream=qr_bytes)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def _context() -> CheckContext:
    return CheckContext(
        format_spec=get_format("A5"),
        industry="Général",
        print_method="Imprimé par getinside",
    )


def test_pipeline_compliant_pdf(tmp_path):
    f = UploadedFile(name="ok.pdf", data=_compliant_pdf())
    doc = Document.from_upload([f])
    # Use an empty logo library so the logo check returns INFO and doesn't
    # block on the missing real logos in the synthetic PDF.
    empty_lib = LogoLibrary(tmp_path)
    results = run_all_checks(doc, _context(), logo_library=empty_lib)

    errors = [r for r in results if r.severity is Severity.ERROR]
    assert errors == [], "\n".join(r.message for r in errors)


def test_pipeline_missing_legal_mention_for_industry_alcool(tmp_path):
    f = UploadedFile(name="alcool.pdf", data=_compliant_pdf())  # no alcool warning text
    doc = Document.from_upload([f])
    empty_lib = LogoLibrary(tmp_path)
    ctx = _context()
    ctx.industry = "Alcool"
    results = run_all_checks(doc, ctx, logo_library=empty_lib)
    assert overall_verdict(results) == "fail"
    assert any(
        r.check_name == "industry" and r.severity is Severity.ERROR for r in results
    )


def test_pipeline_recto_verso_text_aggregates(tmp_path):
    """Mention on verso alone should still satisfy the advertiser check."""
    qr = segno.make("https://gtinsi.de/HELLO2026", error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=10, border=1)
    qr_bytes = buf.getvalue()

    doc = fitz.open()
    # Recto: only QR + offer date + code (no advertiser text)
    page1 = doc.new_page(width=A5_W_PT, height=A5_H_PT)
    page1.insert_text((40, 60), "Offre valable jusqu'au 31/12/2026.", fontsize=10)
    page1.insert_text((40, 80), "Code promo : HELLO2026.", fontsize=10)
    page1.insert_image(fitz.Rect(40, 200, 120, 280), stream=qr_bytes)

    # Verso: full advertiser block
    page2 = doc.new_page(width=A5_W_PT, height=A5_H_PT)
    y = 60
    for line in COMPLIANT_BODY.split(". "):
        if line.strip():
            page2.insert_text((40, y), line.strip() + ".", fontsize=9)
            y += 12
    page2.insert_image(fitz.Rect(40, 400, 120, 480), stream=qr_bytes)

    out = io.BytesIO()
    doc.save(out)
    f = UploadedFile(name="rv.pdf", data=out.getvalue())
    document = Document.from_upload([f])
    empty_lib = LogoLibrary(tmp_path)

    results = run_all_checks(document, _context(), logo_library=empty_lib)
    advertiser_errors = [
        r for r in results if r.check_name == "advertiser" and r.severity is Severity.ERROR
    ]
    assert advertiser_errors == []


def test_severity_override_downgrades_matching_check(pdf_a5_single):
    from preflight.document import Document
    doc = Document.from_upload([pdf_a5_single])
    ctx = CheckContext(
        format_spec=get_format("A5"),
        severity_overrides={"colorspace": Severity.INFO},
    )
    results = run_all_checks(doc, ctx)
    colorspace_results = [r for r in results if r.check_name == "colorspace"]
    assert colorspace_results, "colorspace check must produce results"
    assert all(r.severity is Severity.INFO for r in colorspace_results), (
        "All colorspace results should be downgraded to INFO"
    )


def test_severity_override_does_not_affect_other_checks(pdf_a5_single):
    from preflight.document import Document
    doc = Document.from_upload([pdf_a5_single])
    ctx = CheckContext(
        format_spec=get_format("A5"),
        severity_overrides={"colorspace": Severity.INFO},
    )
    results = run_all_checks(doc, ctx)
    non_colorspace = [r for r in results if r.check_name != "colorspace"]
    assert non_colorspace, "other checks must still run"


def test_severity_override_empty_dict_is_noop(pdf_a5_single):
    from preflight.document import Document
    doc = Document.from_upload([pdf_a5_single])
    ctx_no_override = CheckContext(format_spec=get_format("A5"))
    ctx_empty = CheckContext(format_spec=get_format("A5"), severity_overrides={})
    results_no = run_all_checks(doc, ctx_no_override)
    results_empty = run_all_checks(doc, ctx_empty)
    assert [(r.check_name, r.severity) for r in results_no] == [
        (r.check_name, r.severity) for r in results_empty
    ]
