import io

import pytest
from PIL import Image

from preflight.document import Document, DocumentError, UploadedFile


def test_pdf_single_page(pdf_a5_single):
    doc = Document.from_upload([pdf_a5_single])
    assert doc.kind == "pdf"
    assert doc.page_count == 1
    page = doc.pages[0]
    box = page.dimensions_mm()
    assert abs(box.width - 148.0) < 0.5
    assert abs(box.height - 210.0) < 0.5
    assert "Hello" in page.text_layer()


def test_pdf_recto_verso(pdf_a5_recto_verso):
    doc = Document.from_upload([pdf_a5_recto_verso])
    assert doc.page_count == 2


def test_pdf_three_pages_rejected(pdf_three_pages):
    with pytest.raises(DocumentError, match="recto-verso"):
        Document.from_upload([pdf_three_pages])


def test_encrypted_pdf_rejected(pdf_encrypted):
    with pytest.raises(DocumentError, match="protégé"):
        Document.from_upload([pdf_encrypted])


def test_png_dimensions_via_dpi(png_a5_300dpi):
    doc = Document.from_upload([png_a5_300dpi])
    assert doc.kind == "image"
    assert doc.page_count == 1
    box = doc.pages[0].dimensions_mm()
    assert abs(box.width - 148.0) < 0.5
    assert abs(box.height - 210.0) < 0.5
    assert doc.pages[0].dpi() == pytest.approx(300, abs=0.5)


def test_two_images_recto_verso(png_a5_300dpi, jpeg_a5_cmyk_300dpi):
    f2 = UploadedFile(name="verso.jpg", data=jpeg_a5_cmyk_300dpi.data)
    doc = Document.from_upload([png_a5_300dpi, f2])
    assert doc.page_count == 2


def test_three_images_rejected(png_a5_300dpi):
    files = [
        UploadedFile(name=f"page{i}.png", data=png_a5_300dpi.data) for i in range(3)
    ]
    with pytest.raises(DocumentError, match="maximum"):
        Document.from_upload(files)


def test_mixed_pdf_and_image_rejected(pdf_a5_single, png_a5_300dpi):
    with pytest.raises(DocumentError, match="mélange"):
        Document.from_upload([pdf_a5_single, png_a5_300dpi])


def test_jpeg_cmyk_color_space(jpeg_a5_cmyk_300dpi):
    doc = Document.from_upload([jpeg_a5_cmyk_300dpi])
    spaces = doc.pages[0].color_spaces()
    assert spaces == {"CMYK"} or "CMYK" in spaces


def test_png_color_space(png_a5_300dpi):
    doc = Document.from_upload([png_a5_300dpi])
    spaces = doc.pages[0].color_spaces()
    assert "RGB" in spaces


def test_oversize_rejected():
    big = b"\x00" * (51 * 1024 * 1024)
    f = UploadedFile(name="huge.pdf", data=big)
    with pytest.raises(DocumentError, match="taille maximale"):
        Document.from_upload([f])


def test_corrupt_pdf_rejected():
    f = UploadedFile(name="broken.pdf", data=b"not a pdf")
    with pytest.raises(DocumentError, match="illisible"):
        Document.from_upload([f])


def test_pdf_renders_to_image(pdf_a5_single):
    doc = Document.from_upload([pdf_a5_single])
    img = doc.pages[0].render(dpi=150)
    assert isinstance(img, Image.Image)
    # 148mm @ 150dpi ≈ 874px wide
    assert 850 <= img.width <= 900
