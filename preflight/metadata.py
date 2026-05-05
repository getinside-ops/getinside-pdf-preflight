"""Document metadata extraction and software classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class DocumentMetadata:
    pdf_version: str | None = None
    pdf_x: str | None = None
    creator: str | None = None
    producer: str | None = None
    creation_date: str | None = None
    mod_date: str | None = None
    file_format: str | None = None
    color_mode: str | None = None
    dpi: str | None = None


_PROFESSIONAL = [
    "indesign",
    "illustrator",
    "photoshop",
    "acrobat",
    "distiller",
    "quarkxpress",
    "affinity publisher",
    "affinity designer",
    "coreldraw",
    "scribus",
]

_SUSPICIOUS = [
    "word",
    "powerpoint",
    "excel",
    "libreoffice",
    "openoffice",
    "google docs",
    "canva",
    "chrome",
    "firefox",
    "safari",
    "preview",
    "dopdf",
    "pdfcreator",
    "cutepdf",
    "bullzip",
    "novapdf",
    "primopdf",
]


def _parse_pdf_date(raw: str | None) -> str | None:
    """Parse a PDF date string (D:YYYYMMDDHHmmSS...) into DD/MM/YYYY."""
    if not raw:
        return None
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", raw)
    if not m:
        return None
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"


def _parse_pdf_x_from_xmp(xmp: str) -> str | None:
    """Extract PDF/X version string from raw XMP metadata XML."""
    if not xmp:
        return None
    m = re.search(r"GTS_PDFXVersion[^>]*>([^<]+)<", xmp)
    return m.group(1).strip() if m else None


def software_flag(metadata: DocumentMetadata) -> Literal["professional", "suspicious", "unknown"]:
    """Classify authoring software. Creator field takes precedence over producer."""
    for field_val in (metadata.creator, metadata.producer):
        if not field_val:
            continue
        lower = field_val.lower()
        for term in _SUSPICIOUS:
            if term in lower:
                return "suspicious"
        for term in _PROFESSIONAL:
            if term in lower:
                return "professional"
    return "unknown"
