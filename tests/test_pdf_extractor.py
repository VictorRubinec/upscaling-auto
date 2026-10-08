import pymupdf as fitz
from PIL import Image

from src.pdf_extractor import PdfPageExtractor, parse_page_ranges


def _make_pdf(path, pages=3):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=200, height=300)
        page.insert_text((20, 50), f"Pagina {i + 1}")
    doc.save(str(path))
    doc.close()


def test_parse_page_ranges():
    assert parse_page_ranges(None, 4) == [0, 1, 2, 3]
    assert parse_page_ranges("1-2,4", 4) == [0, 1, 3]
    assert parse_page_ranges("9", 4) == []


def test_extract_all_pages_and_idempotence(tmp_path):
    pdf = tmp_path / "pedido.pdf"
    _make_pdf(pdf)
    out = tmp_path / "out"

    files = PdfPageExtractor.extract(pdf, out, dpi=144)
    assert [f.name for f in files] == ["pedido_p001.png", "pedido_p002.png", "pedido_p003.png"]
    with Image.open(files[0]) as img:
        assert img.size == (400, 600)  # 200x300pt @ 144 DPI

    mtime = files[0].stat().st_mtime_ns
    PdfPageExtractor.extract(pdf, out, dpi=144)
    assert files[0].stat().st_mtime_ns == mtime


def test_extract_page_selection(tmp_path):
    pdf = tmp_path / "a.pdf"
    _make_pdf(pdf)
    files = PdfPageExtractor.extract(pdf, tmp_path / "o", dpi=72, pages="2")
    assert [f.name for f in files] == ["a_p002.png"]
