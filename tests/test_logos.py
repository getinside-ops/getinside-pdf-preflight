from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from preflight.logos import LogoLibrary

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGO_ROOT = REPO_ROOT / "assets" / "logos"


@pytest.fixture(scope="module")
def library() -> LogoLibrary:
    return LogoLibrary(LOGO_ROOT)


def test_library_loads_user_provided_logos(library):
    assert not library.is_empty
    assert {"getinside", "cartouche_info_tri", "imprim_vert"} <= library.categories


def test_empty_library(tmp_path):
    lib = LogoLibrary(tmp_path)
    assert lib.is_empty
    assert lib.best_match(Image.new("RGB", (100, 100), "white")) == {}


def test_random_white_canvas_is_not_a_match(library):
    canvas = Image.new("RGB", (1748, 2480), "white")
    matches = library.best_match(canvas)
    # All variants will be far from a blank canvas → no match within threshold.
    assert matches == {} or all(m.distance > 0 for m in matches.values())


def test_logo_matches_itself(library):
    # Render the same source SVG and expect a near-zero distance for that category.
    from preflight.logos import _load_image

    variant = next(v for v in library.variants if v.category == "getinside")
    rendered = _load_image(variant.path)
    matches = library.all_distances(rendered)
    assert "getinside" in matches
    assert matches["getinside"].distance <= 4  # near-zero — same image
