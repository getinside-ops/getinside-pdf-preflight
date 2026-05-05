# Metadata Display Panel — Design Spec

**Date:** 2026-05-05  
**Status:** Approved

## Summary

Add a metadata strip at the top of the results area (after "Lancer la vérification") that displays file provenance information: PDF version, PDF/X compliance, authoring software, and creation date. Suspicious software triggers an orange warning badge within the strip.

## Architecture

### New module: `preflight/metadata.py`

Single responsibility: extract and classify document metadata. No Streamlit imports.

**Public API:**

```python
@dataclass
class DocumentMetadata:
    pdf_version: str | None       # e.g. "PDF 1.7"
    pdf_x: str | None             # e.g. "PDF/X-4", or None
    creator: str | None           # authoring app
    producer: str | None          # PDF library
    creation_date: str | None     # formatted "DD/MM/YYYY"
    mod_date: str | None          # formatted "DD/MM/YYYY", or None
    # image-only fields
    file_format: str | None       # "JPEG" or "PNG"
    color_mode: str | None        # "CMYK", "RGB", etc.
    dpi: str | None               # e.g. "300"

def extract_metadata(document: Document) -> DocumentMetadata: ...
def software_flag(metadata: DocumentMetadata) -> Literal["professional", "suspicious", "unknown"]: ...
```

**PDF/X detection:** parse `fitz_doc.get_xml_metadata()` with a regex for `GTS_PDFXVersion`. Fall back to `None` if absent or XMP unavailable.

**Date parsing:** strip the PDF date format `D:YYYYMMDDHHmmSS±HH'mm'` into `DD/MM/YYYY`. Return `None` on parse failure.

### Software classification (`preflight/metadata.py`)

Case-insensitive substring match against `creator` and `producer`. First match wins; `creator` takes precedence over `producer`.

**Professional list:** InDesign, Illustrator, Photoshop, Acrobat, Distiller, QuarkXPress, Affinity Publisher, Affinity Designer, CorelDRAW, Scribus

**Suspicious list:** Word, PowerPoint, Excel, LibreOffice, OpenOffice, Google Docs, Canva, Chrome, Firefox, Safari, Preview, doPDF, PDFCreator, CutePDF, Bullzip, novaPDF, PrimoPDF

**Unknown:** anything not matched by either list.

### UI: `app.py`

New `_render_metadata(document: Document) -> None` function. Called immediately after the spinner completes, before `_render_results()`.

Renders a single-line HTML strip styled to match existing card aesthetics (light gray background, 1px border, `border-radius: 10px`, small font ~12px).

**Layout:**

```
📄 PDF 1.7  ·  [pdf_x badge]  ·  [software badge]  ·  📅 DD/MM/YYYY
```

**PDF/X badge:**
- `✅ PDF/X-4` — green text if PDF/X version detected
- `⚠️ Non PDF/X` — orange text if no PDF/X

**Software badge:**
- `✏️ Adobe InDesign 2024` — no special color (professional)
- `⚠️ Microsoft Word` — orange text (suspicious)
- `✏️ <name>` — gray text (unknown)

For image documents: shows `📄 JPEG · 🎨 CMYK · 🖨️ 300 DPI` instead of PDF fields. No software badge for images.

Fields with `None` value are omitted silently from the strip.

## Data Flow

```
run_all_checks() completes
→ extract_metadata(document)          # preflight/metadata.py
→ software_flag(metadata)             # preflight/metadata.py
→ _render_metadata(document)          # app.py — displays strip
→ _render_results(results)            # app.py — existing verdict + checks
```

## Testing

- Unit tests in `tests/test_metadata.py`
- Test PDF date parsing (valid, malformed, None)
- Test PDF/X extraction (present, absent, malformed XMP)
- Test software classification: one professional hit, one suspicious hit, unknown, None creator+producer
- No new integration test needed (metadata extraction is pure function over a Document)

## Out of Scope

- Metadata fields do not become `CheckResult` entries — they stay in the display strip only.
- No severity escalation: suspicious software is always informational, never blocks the check run.
- No user-configurable allowlist/blocklist in this iteration.
