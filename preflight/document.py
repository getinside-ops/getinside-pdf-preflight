"""Document abstraction.

Wraps either a PDF (`fitz.Document`) or 1-2 raster images (PNG/JPEG) and
exposes a uniform `Page` interface to the rest of the preflight pipeline.

Construction goes through `Document.from_upload(files)` so all validation
(file count, size cap, encryption rejection, mixed-type rejection) lives
in one place. The Streamlit layer should never instantiate `Document`
directly with raw bytes.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

PT_TO_MM = 25.4 / 72.0  # 1 PostScript point = 25.4/72 mm
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_IMAGE_PAGES = 2


class DocumentError(ValueError):
    """Raised for any user-facing upload validation failure."""


@dataclass(frozen=True)
class BoxMm:
    width: float
    height: float


class Page:
    """Uniform per-page interface."""

    index: int
    source: str  # "pdf" or "image"

    def dimensions_mm(self) -> BoxMm: ...
    def media_box_mm(self) -> BoxMm | None: ...
    def trim_box_mm(self) -> BoxMm | None: ...
    def dpi(self) -> float | None: ...
    def render(self, dpi: int = 300) -> Image.Image: ...
    def text_layer(self) -> str: ...
    def color_spaces(self) -> set[str]: ...
    def has_trim_marks(self) -> bool: ...
    def safe_zone_violations_mm(self, safe_zone_mm: float) -> list[dict]: ...


class PdfPage(Page):
    source = "pdf"

    def __init__(self, fitz_page: fitz.Page, index: int) -> None:
        self._page = fitz_page
        self.index = index

    def _rect_to_mm(self, rect: fitz.Rect | None) -> BoxMm | None:
        if rect is None:
            return None
        return BoxMm(width=rect.width * PT_TO_MM, height=rect.height * PT_TO_MM)

    def dimensions_mm(self) -> BoxMm:
        # Prefer TrimBox (final size); fall back to MediaBox.
        trim = self.trim_box_mm()
        return trim if trim is not None else self.media_box_mm()

    def media_box_mm(self) -> BoxMm | None:
        return self._rect_to_mm(self._page.mediabox)

    def trim_box_mm(self) -> BoxMm | None:
        # PyMuPDF exposes trimbox if present; otherwise it returns mediabox.
        # We detect "trimbox is really mediabox" by comparing rects.
        try:
            trim = self._page.trimbox
        except AttributeError:
            return None
        media = self._page.mediabox
        if trim is None or trim == media:
            return None
        return self._rect_to_mm(trim)

    def dpi(self) -> float | None:
        return None  # vector / undefined for PDF pages

    def render(self, dpi: int = 300) -> Image.Image:
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = self._page.get_pixmap(matrix=matrix, alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    def text_layer(self) -> str:
        return self._page.get_text("text") or ""

    def trim_box_rect(self) -> "fitz.Rect | None":
        """Raw TrimBox as fitz.Rect (page coordinate space), or None if equal to MediaBox."""
        try:
            trim = self._page.trimbox
        except AttributeError:
            return None
        media = self._page.mediabox
        if trim is None or trim == media:
            return None
        return fitz.Rect(trim)

    def has_trim_marks(self) -> bool:
        """True if strokes exist entirely outside the TrimBox (Illustrator-style trim marks)."""
        trim = self.trim_box_rect()
        if trim is None:
            return False
        try:
            drawings = self._page.get_drawings()
        except Exception:
            return False
        for d in drawings:
            if d.get("type") not in ("s", "fs"):
                continue
            r = d.get("rect")
            if r is None:
                continue
            r = fitz.Rect(r)
            if r.is_empty or r.is_infinite:
                continue
            if not trim.intersects(r):
                return True
        return False

    def safe_zone_violations_mm(self, safe_zone_mm: float) -> list[dict]:
        """Text blocks within safe_zone_mm of the TrimBox edge (inside TrimBox only).
        Returns [] if no TrimBox defined."""
        MM_PER_PT = 25.4 / 72.0
        trim = self.trim_box_rect()
        if trim is None:
            return []
        safe_pt = safe_zone_mm / MM_PER_PT
        safe_rect = fitz.Rect(
            trim.x0 + safe_pt,
            trim.y0 + safe_pt,
            trim.x1 - safe_pt,
            trim.y1 - safe_pt,
        )
        violations: list[dict] = []
        for b in self._page.get_text("blocks"):
            if len(b) < 7 or b[6] != 0:  # skip image blocks (type 1)
                continue
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            if not (isinstance(text, str) and text.strip()):
                continue
            block_rect = fitz.Rect(x0, y0, x1, y1)
            if block_rect.is_empty:
                continue
            if not trim.intersects(block_rect):  # outside TrimBox: trim marks area, skip
                continue
            if safe_rect.contains(block_rect):  # comfortably inside safe zone: OK
                continue
            # Violation: calculate min distance from each TrimBox edge
            dist_l = (block_rect.x0 - trim.x0) * MM_PER_PT
            dist_t = (block_rect.y0 - trim.y0) * MM_PER_PT
            dist_r = (trim.x1 - block_rect.x1) * MM_PER_PT
            dist_b = (trim.y1 - block_rect.y1) * MM_PER_PT
            positive = [d for d in [dist_l, dist_t, dist_r, dist_b] if d >= 0]
            min_dist = round(min(positive), 1) if positive else 0.0
            violations.append({
                "text": text.strip()[:50].replace("\n", " "),
                "min_dist_mm": min_dist,
            })
        return violations

    def color_spaces(self) -> set[str]:
        spaces: set[str] = set()
        for img in self._page.get_images(full=True):
            xref = img[0]
            try:
                info = self._page.parent.extract_image(xref)
            except Exception:
                continue
            cs = (info.get("colorspace_name") or "").upper()
            if not cs:
                n = info.get("colorspace")
                cs = {1: "GRAY", 3: "RGB", 4: "CMYK"}.get(n, "")
            if cs:
                spaces.add(cs)
        return spaces


class ImagePage(Page):
    source = "image"

    def __init__(self, image: Image.Image, index: int, filename: str) -> None:
        self._image = image
        self.index = index
        self.filename = filename

    def dimensions_mm(self) -> BoxMm:
        d = self.dpi() or 72.0
        return BoxMm(
            width=self._image.width / d * 25.4,
            height=self._image.height / d * 25.4,
        )

    def media_box_mm(self) -> BoxMm | None:
        return None

    def trim_box_mm(self) -> BoxMm | None:
        return None

    def dpi(self) -> float | None:
        info_dpi = self._image.info.get("dpi")
        if info_dpi:
            x, _ = info_dpi
            return float(x) if x else None
        # Try EXIF for JPEG.
        try:
            exif = self._image.getexif()
            x_res = exif.get(282)  # XResolution tag
            unit = exif.get(296, 2)  # ResolutionUnit; 2 = inches, 3 = cm
            if x_res:
                v = float(x_res)
                return v if unit == 2 else v * 2.54
        except Exception:
            pass
        return None

    def render(self, dpi: int = 300) -> Image.Image:
        # The image is already raster; ignore the requested dpi.
        return self._image

    def text_layer(self) -> str:
        return ""

    def color_spaces(self) -> set[str]:
        mode = self._image.mode
        return {
            "RGB": "RGB",
            "RGBA": "RGB",
            "L": "GRAY",
            "LA": "GRAY",
            "P": "INDEXED",
            "CMYK": "CMYK",
            "1": "GRAY",
        }.get(mode, mode.upper())  # type: ignore[return-value]

    def has_trim_marks(self) -> bool:
        return False

    def safe_zone_violations_mm(self, safe_zone_mm: float) -> list[dict]:
        return []

    def color_mode(self) -> str:
        return self._image.mode

    def file_format(self) -> str:
        suffix = Path(self.filename).suffix.lower().lstrip(".")
        if suffix in {"jpg", "jpeg"}:
            return "jpeg"
        if suffix == "png":
            return "png"
        return suffix or "image"


@dataclass(frozen=True)
class UploadedFile:
    """Minimal interface matching streamlit's UploadedFile."""

    name: str
    data: bytes


class Document:
    def __init__(self, pages: list[Page], kind: str, *, fitz_doc: fitz.Document | None = None) -> None:
        self.pages: list[Page] = pages
        self.kind: str = kind  # "pdf" or "image"
        self._fitz_doc = fitz_doc

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @classmethod
    def from_upload(cls, files: list[UploadedFile]) -> "Document":
        if not files:
            raise DocumentError("Aucun fichier fourni.")

        for f in files:
            if len(f.data) > MAX_UPLOAD_BYTES:
                raise DocumentError(
                    f"{f.name} dépasse la taille maximale de {MAX_UPLOAD_BYTES // (1024 * 1024)} Mo."
                )

        suffixes = {Path(f.name).suffix.lower() for f in files}
        if any(s == ".pdf" for s in suffixes) and any(s != ".pdf" for s in suffixes):
            raise DocumentError(
                "Veuillez envoyer soit un seul PDF, soit une à deux images (PNG/JPEG), pas un mélange."
            )

        if all(s == ".pdf" for s in suffixes):
            if len(files) != 1:
                raise DocumentError("Un seul fichier PDF est attendu.")
            return cls._from_pdf(files[0])

        return cls._from_images(files)

    @classmethod
    def _from_pdf(cls, file: UploadedFile) -> "Document":
        try:
            doc = fitz.open(stream=file.data, filetype="pdf")
        except Exception as exc:
            raise DocumentError(f"PDF illisible : {exc}") from exc

        if doc.is_encrypted:
            raise DocumentError(
                "Le PDF est protégé par mot de passe. Veuillez fournir une version non protégée."
            )
        if doc.page_count > 2:
            raise DocumentError(
                f"Le PDF contient {doc.page_count} pages. Seuls les flyers recto ou recto-verso (1-2 pages) sont supportés."
            )
        if doc.page_count == 0:
            raise DocumentError("Le PDF ne contient aucune page.")

        pages = [PdfPage(doc[i], i) for i in range(doc.page_count)]
        return cls(pages, kind="pdf", fitz_doc=doc)

    @classmethod
    def _from_images(cls, files: list[UploadedFile]) -> "Document":
        if len(files) > MAX_IMAGE_PAGES:
            raise DocumentError(
                f"Au maximum {MAX_IMAGE_PAGES} images (recto + verso) peuvent être envoyées."
            )

        pages: list[Page] = []
        for idx, f in enumerate(files):
            try:
                img = Image.open(io.BytesIO(f.data))
                img.load()
            except Exception as exc:
                raise DocumentError(f"Image illisible ({f.name}) : {exc}") from exc
            pages.append(ImagePage(img, idx, f.name))
        return cls(pages, kind="image")


__all__ = [
    "BoxMm",
    "Document",
    "DocumentError",
    "ImagePage",
    "MAX_IMAGE_PAGES",
    "MAX_UPLOAD_BYTES",
    "Page",
    "PdfPage",
    "UploadedFile",
]
