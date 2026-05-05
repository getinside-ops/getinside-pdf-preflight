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
