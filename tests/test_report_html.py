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


def test_error_card_is_open_by_default(ctx):
    results = [_r("dimensions", Severity.ERROR, "Taille incorrecte")]
    html = build_html_report(results, ctx)
    assert "<details open>" in html


def test_ok_card_is_collapsed_by_default(ctx):
    results = [_r("colorspace", Severity.INFO, "OK")]
    html = build_html_report(results, ctx)
    assert "<details>" in html
    assert "<details open>" not in html


def test_error_card_has_red_icon(ctx):
    results = [_r("dimensions", Severity.ERROR, "Taille incorrecte")]
    html = build_html_report(results, ctx)
    # Check for error icon styling: red bg, border, and text
    assert "#fef2f2" in html  # error icon bg
    assert "#fca5a5" in html  # error icon border
    assert "✕" in html  # error icon char


def test_warning_card_has_amber_icon(ctx):
    results = [_r("colorspace", Severity.WARNING, "Couleur non CMJN")]
    html = build_html_report(results, ctx)
    # Check for warning icon styling: amber bg, border, and text
    assert "#fffbeb" in html  # warning icon bg
    assert "#fcd34d" in html  # warning icon border
    assert "!" in html  # warning icon char


def test_ok_card_has_green_icon(ctx):
    results = [_r("logos", Severity.INFO, "Logo détecté")]
    html = build_html_report(results, ctx)
    # Check for info icon styling: green bg, border, and text
    assert "#f0fdf4" in html  # info icon bg
    assert "#86efac" in html  # info icon border
    assert "✓" in html  # info icon char


def test_warning_card_is_open_by_default(ctx):
    results = [_r("colorspace", Severity.WARNING, "Couleur non CMJN")]
    html = build_html_report(results, ctx)
    assert "<details open>" in html


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
