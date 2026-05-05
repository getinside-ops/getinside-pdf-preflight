# Metadata Display Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display a compact metadata strip (PDF version, PDF/X status, authoring software with suspicious-software flagging, creation date) above the verdict banner after running preflight checks.

**Architecture:** New `preflight/metadata.py` module exposes `DocumentMetadata` dataclass + `extract_metadata()` + `software_flag()`. `app.py` gains `_render_metadata()` which renders the strip between the spinner and `_render_results()`. No business logic in `app.py`.

**Tech Stack:** PyMuPDF (`fitz`), Pillow, Streamlit, pytest

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `preflight/metadata.py` | Data extraction and software classification |
| Create | `tests/test_metadata.py` | Unit tests for all metadata logic |
| Modify | `app.py` | Add `_render_metadata()`, call it after the spinner |

---

### Task 1: Core data types and pure helpers

**Files:**
- Create: `preflight/metadata.py`
- Create: `tests/test_metadata.py`

- [ ] **Step 1: Write failing tests for `_parse_pdf_date` and `_parse_pdf_x_from_xmp`**

Create `tests/test_metadata.py`:

```python
"""Tests for preflight/metadata.py."""
from __future__ import annotations

from preflight.metadata import (
    DocumentMetadata,
    _parse_pdf_date,
    _parse_pdf_x_from_xmp,
    software_flag,
)


# --- _parse_pdf_date ---

def test_parse_pdf_date_full():
    assert _parse_pdf_date("D:20241205143022+01'00'") == "05/12/2024"


def test_parse_pdf_date_short():
    assert _parse_pdf_date("D:20230101") == "01/01/2023"


def test_parse_pdf_date_none():
    assert _parse_pdf_date(None) is None


def test_parse_pdf_date_malformed():
    assert _parse_pdf_date("not-a-date") is None


def test_parse_pdf_date_empty():
    assert _parse_pdf_date("") is None


# --- _parse_pdf_x_from_xmp ---

def test_parse_pdf_x_found():
    xmp = '<rdf:Description rdf:about=""><pdfxid:GTS_PDFXVersion>PDF/X-4</pdfxid:GTS_PDFXVersion></rdf:Description>'
    assert _parse_pdf_x_from_xmp(xmp) == "PDF/X-4"


def test_parse_pdf_x_found_without_namespace():
    xmp = "<GTS_PDFXVersion>PDF/X-1a:2001</GTS_PDFXVersion>"
    assert _parse_pdf_x_from_xmp(xmp) == "PDF/X-1a:2001"


def test_parse_pdf_x_absent():
    assert _parse_pdf_x_from_xmp("<rdf:Description/>") is None


def test_parse_pdf_x_empty_string():
    assert _parse_pdf_x_from_xmp("") is None


def test_parse_pdf_x_malformed_xmp():
    assert _parse_pdf_x_from_xmp("<?xml version='1.0'?><broken>") is None


# --- software_flag ---

def test_flag_professional_indesign():
    meta = DocumentMetadata(creator="Adobe InDesign 19.4")
    assert software_flag(meta) == "professional"


def test_flag_professional_photoshop():
    meta = DocumentMetadata(creator="Adobe Photoshop 25.0")
    assert software_flag(meta) == "professional"


def test_flag_professional_illustrator():
    meta = DocumentMetadata(creator="Adobe Illustrator 28.0")
    assert software_flag(meta) == "professional"


def test_flag_suspicious_word():
    meta = DocumentMetadata(creator="Microsoft Word")
    assert software_flag(meta) == "suspicious"


def test_flag_suspicious_canva():
    meta = DocumentMetadata(creator="Canva")
    assert software_flag(meta) == "suspicious"


def test_flag_suspicious_browser():
    meta = DocumentMetadata(creator="Chrome")
    assert software_flag(meta) == "suspicious"


def test_flag_suspicious_in_producer():
    meta = DocumentMetadata(creator=None, producer="doPDF")
    assert software_flag(meta) == "suspicious"


def test_flag_creator_beats_producer():
    # creator is professional, producer is suspicious — creator wins
    meta = DocumentMetadata(creator="Adobe InDesign", producer="LibreOffice PDF Export")
    assert software_flag(meta) == "professional"


def test_flag_unknown():
    meta = DocumentMetadata(creator="SomeOtherApp 3.0")
    assert software_flag(meta) == "unknown"


def test_flag_both_none():
    meta = DocumentMetadata()
    assert software_flag(meta) == "unknown"


def test_flag_case_insensitive():
    meta = DocumentMetadata(creator="MICROSOFT WORD 365")
    assert software_flag(meta) == "suspicious"
```

- [ ] **Step 2: Run tests — expect import errors**

```bash
cd "/Users/benoitprentout/github repos/getinside-pdf-preflight"
.venv/bin/pytest tests/test_metadata.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'preflight.metadata'`

- [ ] **Step 3: Create `preflight/metadata.py` with data types and pure helpers**

```python
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
```

- [ ] **Step 4: Run tests — expect all to pass**

```bash
.venv/bin/pytest tests/test_metadata.py -v
```

Expected: all 22 tests PASS

- [ ] **Step 5: Commit**

```bash
rtk git add preflight/metadata.py tests/test_metadata.py
rtk git commit -m "feat: add DocumentMetadata type and pure helpers (date parsing, PDF/X, software flag)"
```

---

### Task 2: `extract_metadata()` function

**Files:**
- Modify: `preflight/metadata.py`
- Modify: `tests/test_metadata.py`

- [ ] **Step 1: Write failing tests for `extract_metadata`**

Add to the bottom of `tests/test_metadata.py`:

```python
import io
import fitz
from PIL import Image
from preflight.document import Document, ImagePage, UploadedFile
from preflight.metadata import extract_metadata


def _pdf_with_meta(creator: str = "", producer: str = "", creation_date: str = "") -> bytes:
    doc = fitz.open()
    doc.new_page()
    doc.set_metadata({
        "creator": creator,
        "producer": producer,
        "creationDate": creation_date,
    })
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def _png_bytes(mode: str = "RGB", dpi: int = 300) -> bytes:
    img = Image.new(mode, (100, 100), color="white" if mode != "CMYK" else (0, 0, 0, 0))
    out = io.BytesIO()
    img.save(out, format="PNG", dpi=(dpi, dpi))
    return out.getvalue()


def _jpeg_bytes(mode: str = "CMYK", dpi: int = 300) -> bytes:
    img = Image.new(mode, (100, 100), color=(0, 0, 0, 0) if mode == "CMYK" else "white")
    out = io.BytesIO()
    img.save(out, format="JPEG", dpi=(dpi, dpi))
    return out.getvalue()


def test_extract_pdf_creator_and_version():
    data = _pdf_with_meta(creator="Adobe InDesign 2024", producer="Adobe PDF Library 16.0")
    doc = Document.from_upload([UploadedFile(name="x.pdf", data=data)])
    meta = extract_metadata(doc)
    assert meta.creator == "Adobe InDesign 2024"
    assert meta.producer == "Adobe PDF Library 16.0"
    assert meta.pdf_version is not None and "PDF" in meta.pdf_version


def test_extract_pdf_date_parsed():
    data = _pdf_with_meta(creation_date="D:20241205143022+01'00'")
    doc = Document.from_upload([UploadedFile(name="x.pdf", data=data)])
    meta = extract_metadata(doc)
    assert meta.creation_date == "05/12/2024"


def test_extract_pdf_no_pdfx_by_default():
    data = _pdf_with_meta()
    doc = Document.from_upload([UploadedFile(name="x.pdf", data=data)])
    meta = extract_metadata(doc)
    assert meta.pdf_x is None


def test_extract_empty_creator_becomes_none():
    data = _pdf_with_meta(creator="")
    doc = Document.from_upload([UploadedFile(name="x.pdf", data=data)])
    meta = extract_metadata(doc)
    assert meta.creator is None


def test_extract_png_image():
    data = _png_bytes(mode="RGB", dpi=300)
    doc = Document.from_upload([UploadedFile(name="img.png", data=data)])
    meta = extract_metadata(doc)
    assert meta.file_format == "PNG"
    assert meta.color_mode == "RGB"
    assert meta.dpi == "300"


def test_extract_jpeg_cmyk():
    data = _jpeg_bytes(mode="CMYK", dpi=150)
    doc = Document.from_upload([UploadedFile(name="img.jpg", data=data)])
    meta = extract_metadata(doc)
    assert meta.file_format == "JPEG"
    assert meta.color_mode == "CMYK"
    assert meta.dpi == "150"
```

- [ ] **Step 2: Run tests — expect failures on `extract_metadata`**

```bash
.venv/bin/pytest tests/test_metadata.py -k "extract" -v 2>&1 | head -30
```

Expected: `ImportError: cannot import name 'extract_metadata'`

- [ ] **Step 3: Implement `extract_metadata()` in `preflight/metadata.py`**

Add after the `software_flag` function (do not remove any existing code):

```python
def extract_metadata(document: "Document") -> DocumentMetadata:  # type: ignore[name-defined]
    """Extract metadata from a Document (PDF or image)."""
    from preflight.document import ImagePage  # local import avoids circular dep at module level

    if document.kind == "pdf" and document._fitz_doc is not None:
        fitz_doc = document._fitz_doc
        raw = fitz_doc.metadata or {}

        try:
            xmp = fitz_doc.get_xml_metadata() or ""
        except Exception:
            xmp = ""

        return DocumentMetadata(
            pdf_version=raw.get("format") or None,
            pdf_x=_parse_pdf_x_from_xmp(xmp),
            creator=raw.get("creator") or None,
            producer=raw.get("producer") or None,
            creation_date=_parse_pdf_date(raw.get("creationDate")),
            mod_date=_parse_pdf_date(raw.get("modDate")),
        )

    # Image document — use first page
    if document.pages:
        page = document.pages[0]
        if isinstance(page, ImagePage):
            dpi = page.dpi()
            return DocumentMetadata(
                file_format=page.file_format().upper(),
                color_mode=page._image.mode,
                dpi=str(int(dpi)) if dpi else None,
            )

    return DocumentMetadata()
```

Also append `__all__` to the bottom of the file (public API only):

```python
__all__ = [
    "DocumentMetadata",
    "extract_metadata",
    "software_flag",
]
```

- [ ] **Step 4: Run all metadata tests**

```bash
.venv/bin/pytest tests/test_metadata.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Run full suite to check for regressions**

```bash
.venv/bin/pytest -q
```

Expected: same pass count as before (91 tests), 0 new failures

- [ ] **Step 6: Commit**

```bash
rtk git add preflight/metadata.py tests/test_metadata.py
rtk git commit -m "feat: implement extract_metadata for PDF and image documents"
```

---

### Task 3: UI — metadata strip in `app.py`

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add the import at the top of `app.py`**

After the existing imports block (after line `from preflight.logos import LogoLibrary`), add:

```python
from preflight.metadata import extract_metadata, software_flag
```

- [ ] **Step 2: Add `_render_metadata()` helper to `app.py`**

Add this function in the `# ---------- Helpers -----------------------------------------------------------` section, after the existing `_verdict_banner` function (after line ~167):

```python
def _render_metadata(document: Document) -> None:
    meta = extract_metadata(document)
    flag = software_flag(meta)
    parts: list[str] = []

    if document.kind == "pdf":
        if meta.pdf_version:
            parts.append(f"<span style='color:#374151'>📄 {meta.pdf_version}</span>")

        if meta.pdf_x:
            parts.append(f"<span style='color:#16a34a;font-weight:600'>✅ {meta.pdf_x}</span>")
        else:
            parts.append("<span style='color:#d97706;font-weight:600'>⚠️ Non PDF/X</span>")

        software_name = meta.creator or meta.producer
        if software_name:
            if flag == "suspicious":
                parts.append(
                    f"<span style='color:#d97706;font-weight:600'>⚠️ {software_name}</span>"
                )
            else:
                parts.append(f"<span style='color:#6b7280'>✏️ {software_name}</span>")

        if meta.creation_date:
            parts.append(f"<span style='color:#6b7280'>📅 {meta.creation_date}</span>")

    else:  # image
        if meta.file_format:
            parts.append(f"<span style='color:#374151'>📄 {meta.file_format}</span>")
        if meta.color_mode:
            parts.append(f"<span style='color:#374151'>🎨 {meta.color_mode}</span>")
        if meta.dpi:
            parts.append(f"<span style='color:#374151'>🖨️ {meta.dpi} DPI</span>")

    if not parts:
        return

    sep = "<span style='color:#d1d5db'>&nbsp;·&nbsp;</span>"
    st.markdown(
        "<div style='border:1px solid #e5e7eb;background:#f9fafb;"
        "border-radius:10px;padding:8px 14px;margin-bottom:12px;"
        f"font-size:12px;line-height:1.8'>{sep.join(parts)}</div>",
        unsafe_allow_html=True,
    )
```

- [ ] **Step 3: Call `_render_metadata()` after the spinner, before `_render_results()`**

In the `# ---------- Run ---------------------------------------------------------------` section, find this block (around line 244):

```python
    with st.spinner("Analyse en cours…"):
        results = run_all_checks(document, context, logo_library=library)

    _render_results(results)
```

Replace with:

```python
    with st.spinner("Analyse en cours…"):
        results = run_all_checks(document, context, logo_library=library)

    _render_metadata(document)
    _render_results(results)
```

- [ ] **Step 4: Run the full test suite to confirm no regressions**

```bash
.venv/bin/pytest -q
```

Expected: same pass count as before, 0 new failures

- [ ] **Step 5: Start the app and verify the metadata strip visually**

```bash
.venv/bin/streamlit run app.py --server.port 8766
```

Upload a PDF and click "Lancer la vérification". Verify:
- The strip appears above the verdict banner
- PDF version (e.g. "PDF 1.7") is shown
- "⚠️ Non PDF/X" appears in orange (a plain fitz-generated PDF has no PDF/X)
- Software name appears if creator/producer are set
- No strip for image uploads (or image fields shown instead)

- [ ] **Step 6: Commit**

```bash
rtk git add app.py
rtk git commit -m "feat: add metadata strip above verdict banner with PDF/X and software flagging"
```
