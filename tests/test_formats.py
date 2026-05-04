import pytest

from preflight.formats import FORMATS, custom_format, get_format


def test_all_named_formats_present():
    assert {"A5", "A6", "Carte cadeau", "15 x 10 cm"} <= set(FORMATS)


def test_a5_final_dimensions_match():
    a5 = get_format("A5")
    ok, kind = a5.matches_dimensions(148.0, 210.0)
    assert ok and kind == "final"


def test_a5_bleed_dimensions_match():
    a5 = get_format("A5")
    ok, kind = a5.matches_dimensions(152.0, 214.0)
    assert ok and kind == "bleed"


def test_a5_landscape_orientation_accepted():
    a5 = get_format("A5")
    ok, kind = a5.matches_dimensions(210.0, 148.0)
    assert ok and kind == "final"


def test_a5_within_tolerance():
    a5 = get_format("A5")
    ok, _ = a5.matches_dimensions(148.5, 210.7)
    assert ok


def test_a5_out_of_tolerance():
    a5 = get_format("A5")
    ok, kind = a5.matches_dimensions(150.0, 210.0)
    assert not ok and kind is None


@pytest.mark.parametrize(
    "fmt_name, w, h",
    [
        ("A6", 105.0, 148.0),
        ("A6", 109.0, 152.0),
        ("Carte cadeau", 105.0, 148.0),
        ("15 x 10 cm", 150.0, 100.0),
        ("15 x 10 cm", 154.0, 104.0),
    ],
)
def test_other_format_dimensions(fmt_name, w, h):
    spec = get_format(fmt_name)
    ok, _ = spec.matches_dimensions(w, h)
    assert ok


def test_custom_format():
    spec = custom_format(120.0, 180.0)
    assert spec.name == "Custom"
    ok, kind = spec.matches_dimensions(120.0, 180.0)
    assert ok and kind == "final"
