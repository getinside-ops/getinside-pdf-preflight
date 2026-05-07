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
    page_renders: dict[int, Image.Image] = field(default_factory=dict)
    page_image_info: dict[int, list[dict]] = field(default_factory=dict)
    page_fonts: dict[int, list] = field(default_factory=dict)
    _document: Document = field(default=None, repr=False)

    @classmethod
    def build(cls, document: Document) -> "DocumentSnapshot":
        snap = cls()
        snap._document = document
        for page in document.pages:
            if page.source == "pdf":
                snap.page_image_info[page.index] = page._page.get_image_info(hashes=False)
                snap.page_fonts[page.index] = page._page.get_fonts(full=True)
        return snap

    def get_page_render(self, page_index: int, dpi: int = SNAPSHOT_RENDER_DPI) -> Image.Image:
        """Lazily render a page when needed."""
        if page_index not in self.page_renders:
            page = self._document.pages[page_index]
            self.page_renders[page_index] = page.render(dpi=dpi)
        return self.page_renders[page_index]


__all__ = ["DocumentSnapshot", "SNAPSHOT_RENDER_DPI"]
