"""DocumentSnapshot — pre-parsed, per-run cache of expensive document operations.

Built once by the pipeline before the check loop starts. Passed to checks
that need it so they can skip redundant re-computation (page renders, font
lists, per-image geometry).

Only PDF pages contribute to page_image_info and page_fonts — image-mode
documents leave those dicts empty.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image

from preflight.document import Document

SNAPSHOT_RENDER_DPI = 300


@dataclass
class DocumentSnapshot:
    # page index → 300dpi render (PDF: rasterized; image: raw image)
    page_renders: dict[int, Image.Image] = field(default_factory=dict)
    # page index → get_image_info(hashes=False) result (PDF pages only)
    page_image_info: dict[int, list[dict]] = field(default_factory=dict)
    # page index → get_fonts(full=True) result (PDF pages only)
    page_fonts: dict[int, list] = field(default_factory=dict)

    @classmethod
    def build(cls, document: Document) -> "DocumentSnapshot":
        snap = cls()
        for page in document.pages:
            if page.source == "pdf":
                snap.page_renders[page.index] = page.render(dpi=SNAPSHOT_RENDER_DPI)
                snap.page_image_info[page.index] = page._page.get_image_info(hashes=False)
                snap.page_fonts[page.index] = page._page.get_fonts(full=True)
            else:
                snap.page_renders[page.index] = page.render()
        return snap


__all__ = ["DocumentSnapshot", "SNAPSHOT_RENDER_DPI"]
