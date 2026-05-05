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


# --- extract_metadata ---

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
    # PNG DPI may have floating-point rounding; check within 1 DPI
    assert meta.dpi is not None and abs(int(meta.dpi) - 300) <= 1


def test_extract_jpeg_cmyk():
    data = _jpeg_bytes(mode="CMYK", dpi=150)
    doc = Document.from_upload([UploadedFile(name="img.jpg", data=data)])
    meta = extract_metadata(doc)
    assert meta.file_format == "JPEG"
    assert meta.color_mode == "CMYK"
    assert meta.dpi == "150"
