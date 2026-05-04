"""Print format specifications.

A `FormatSpec` captures the trim (final) size, expected bleed, safe-zone,
dimensional tolerance, and minimum DPI for a named print format. The
preflight check accepts a page that matches either:

* the trim size (no bleed included), or
* the trim size + 2 × bleed on each axis (bleed-included size),

within `tolerance_mm` on each side.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormatSpec:
    name: str
    final_w_mm: float
    final_h_mm: float
    bleed_mm: float = 2.0
    safe_zone_mm: float = 3.0
    tolerance_mm: float = 1.0
    min_dpi: int = 300

    @property
    def bleed_w_mm(self) -> float:
        return self.final_w_mm + 2 * self.bleed_mm

    @property
    def bleed_h_mm(self) -> float:
        return self.final_h_mm + 2 * self.bleed_mm

    def matches_dimensions(
        self, w_mm: float, h_mm: float
    ) -> tuple[bool, str | None]:
        """Return (ok, kind) where kind is 'final', 'bleed', or None.

        Orientation-agnostic: portrait and landscape both accepted.
        """
        candidates = (
            ("final", self.final_w_mm, self.final_h_mm),
            ("bleed", self.bleed_w_mm, self.bleed_h_mm),
        )
        tol = self.tolerance_mm
        for kind, cw, ch in candidates:
            if (abs(w_mm - cw) <= tol and abs(h_mm - ch) <= tol) or (
                abs(w_mm - ch) <= tol and abs(h_mm - cw) <= tol
            ):
                return True, kind
        return False, None


# Registry of supported formats. "Custom" is built dynamically from user input.
FORMATS: dict[str, FormatSpec] = {
    "A5": FormatSpec("A5", 148.0, 210.0),
    "A6": FormatSpec("A6", 105.0, 148.0),
    "Carte cadeau": FormatSpec("Carte cadeau", 105.0, 148.0),
    "15 x 10 cm": FormatSpec("15 x 10 cm", 150.0, 100.0),
}

FORMAT_NAMES = [*FORMATS.keys(), "Custom"]


def custom_format(width_mm: float, height_mm: float) -> FormatSpec:
    return FormatSpec("Custom", float(width_mm), float(height_mm))


def get_format(name: str) -> FormatSpec | None:
    return FORMATS.get(name)


__all__ = [
    "FormatSpec",
    "FORMATS",
    "FORMAT_NAMES",
    "custom_format",
    "get_format",
]
