"""Logo detection by perceptual hash (phash).

Each subdirectory under ``assets/logos/`` is a *category* (e.g.
``cartouche_info_tri``, ``getinside``). Files inside are *variants* of
that category; we accept PNG/JPEG/SVG. SVG files are rasterized via
PyMuPDF on load.

Detection compares the phash of the rendered page against every variant
phash in the library and returns the best (lowest Hamming distance)
match per category. A distance ≤ ``threshold`` is considered a match.

Limitation by design: this is a *whole-page* phash, so it confirms the
page contains imagery similar to a known variant. It does not localize
the logo on the page. The plan calls this out: the goal is honest
verification, not pretend-precise template matching.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz
import imagehash
from PIL import Image

DEFAULT_THRESHOLD = 18  # phash bits; 64-bit hash, 0=identical, 64=opposite
SOFT_THRESHOLD = 28     # distance above this → likely absent; between 18-28 → warn
SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".svg"}
SVG_RENDER_DPI = 300

# Multi-scale crop fractions of the page's short side. Small fractions
# catch tiny logos (8-15 mm) buried in busy full-page artwork; the
# whole-page entry keeps identical-size references from drifting up.
CROP_FRACTIONS = (0.06, 0.10, 0.18, 0.30, 0.45, 0.65)
CROP_STRIDE_FACTOR = 0.5


def _candidate_crops(image: Image.Image) -> list[Image.Image]:
    """Yield the full image plus a multi-scale grid of square crops.

    The whole page is included so identical-size matches still hit; the
    crops let small logos on a large page get fairly compared.
    """
    crops: list[Image.Image] = [image]
    w, h = image.size
    short = min(w, h)
    for fraction in CROP_FRACTIONS:
        side = int(short * fraction)
        if side < 64:
            continue
        step = max(1, int(side * CROP_STRIDE_FACTOR))
        # range stops so the last tile fits; ensure we cover the right/bottom edge.
        xs = list(range(0, max(1, w - side + 1), step))
        ys = list(range(0, max(1, h - side + 1), step))
        if xs[-1] + side < w:
            xs.append(w - side)
        if ys[-1] + side < h:
            ys.append(h - side)
        for y in ys:
            for x in xs:
                crops.append(image.crop((x, y, x + side, y + side)))
    return crops


def _load_image(path: Path) -> Image.Image:
    suffix = path.suffix.lower()
    if suffix == ".svg":
        doc = fitz.open(str(path))
        try:
            page = doc[0]
            zoom = SVG_RENDER_DPI / 72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        finally:
            doc.close()
    return Image.open(path).convert("RGB")


@dataclass(frozen=True)
class LogoVariant:
    category: str
    name: str
    path: Path
    phash: imagehash.ImageHash


@dataclass(frozen=True)
class LogoMatch:
    category: str
    variant: str
    distance: int

    @property
    def confidence(self) -> float:
        # 64-bit phash; map distance to 0..1 (1 = perfect)
        return max(0.0, 1.0 - self.distance / 64.0)


class LogoLibrary:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.variants: list[LogoVariant] = []
        if root.exists():
            self._load()

    def _load(self) -> None:
        for category_dir in sorted(p for p in self.root.iterdir() if p.is_dir()):
            for file in sorted(category_dir.iterdir()):
                if file.suffix.lower() not in SUPPORTED_EXTS:
                    continue
                try:
                    image = _load_image(file)
                except Exception:
                    continue
                ph = imagehash.phash(image)
                self.variants.append(
                    LogoVariant(
                        category=category_dir.name,
                        name=file.stem,
                        path=file,
                        phash=ph,
                    )
                )

    @property
    def is_empty(self) -> bool:
        return not self.variants

    @property
    def categories(self) -> set[str]:
        return {v.category for v in self.variants}

    def _scan(self, image: Image.Image) -> dict[str, LogoMatch]:
        """Compute the minimum phash distance per category over a multi-scale
        crop sweep of ``image``. Exits early if perfect match found."""
        best_per_cat: dict[str, LogoMatch] = {}
        for crop in _candidate_crops(image):
            crop_hash = imagehash.phash(crop)
            for variant in self.variants:
                distance = int(crop_hash - variant.phash)
                current = best_per_cat.get(variant.category)
                if current is None or distance < current.distance:
                    best_per_cat[variant.category] = LogoMatch(
                        category=variant.category,
                        variant=variant.name,
                        distance=distance,
                    )
                # Early exit: perfect match found
                if distance == 0:
                    return best_per_cat
        return best_per_cat

    def best_match(
        self, image: Image.Image, *, threshold: int = DEFAULT_THRESHOLD
    ) -> dict[str, LogoMatch]:
        """Return the best match per category present in the library.

        Only categories whose best variant is within ``threshold`` are
        included in the returned dict.
        """
        if self.is_empty:
            return {}
        return {
            cat: m for cat, m in self._scan(image).items() if m.distance <= threshold
        }

    def all_distances(self, image: Image.Image) -> dict[str, LogoMatch]:
        """Return the best match per category regardless of threshold."""
        if self.is_empty:
            return {}
        return self._scan(image)


__all__ = [
    "DEFAULT_THRESHOLD",
    "SOFT_THRESHOLD",
    "LogoLibrary",
    "LogoMatch",
    "LogoVariant",
    "SUPPORTED_EXTS",
]
