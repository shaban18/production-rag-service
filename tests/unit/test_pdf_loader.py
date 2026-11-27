"""Unit tests for the PDF loader. PDFs are generated programmatically."""
from pathlib import Path
import pymupdf
import pytest
from app.ingestion.pdf_loader import load_pdf_document
def build_pdf(path: Path, page_texts: list[str], **save_options) -> Path:
    """Create a PDF with one page per entry; "" gives a blank page."""
    doc = pymupdf.open()
    for text in page_texts:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    doc.save(path, **save_options)
    doc.close()
    return path
def test_normal_single_page_pdf(tmp_path: Path) -> None:
    path = build_pdf(tmp_path / "one.pdf", ["Hello PDF world"])
    document = load_pdf_document(path)
    assert document.file_type == "pdf"
    assert document.source_filename == "one.pdf"
    assert len(document.pages) == 1
    assert document.pages[0].page_number == 1
    assert "Hello PDF world" in document.pages[0].text
    assert len(document.document_id) == 64
def test_multi_page_pdf_numbers_pages_from_one(tmp_path: Path) -> None:
    path = build_pdf(tmp_path / "three.pdf", ["alpha", "bravo", "charlie"])
    document = load_pdf_document(path)
    assert [p.page_number for p in document.pages] == [1, 2, 3]
    assert "alpha" in document.pages[0].text
    assert "bravo" in document.pages[1].text
    assert "charlie" in document.pages[2].text
def test_blank_middle_page_keeps_its_number(tmp_path: Path) -> None:
    path = build_pdf(tmp_path / "gap.pdf", ["first", "", "third"])
    document = load_pdf_document(path)
    assert [p.page_number for p in document.pages] == [1, 2, 3]
    assert document.pages[1].text.strip() == ""
    assert "third" in document.pages[2].text
def test_accented_latin_text(tmp_path: Path) -> None:
    path = build_pdf(tmp_path / "accents.pdf", ["Caf\u00e9 r\u00e9sum\u00e9"])
    document = load_pdf_document(path)
    assert "Caf\u00e9" in document.pages[0].text
def test_pdf_with_only_blank_pages_is_rejected(tmp_path: Path) -> None:
    path = build_pdf(tmp_path / "blank.pdf", ["", ""])
    with pytest.raises(ValueError, match="no extractable text"):
        load_pdf_document(path)
def test_image_only_pdf_is_rejected(tmp_path: Path) -> None:
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 60, 60), False)
    pixmap.set_rect(pixmap.irect, (255, 0, 0))
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_image(pymupdf.Rect(72, 72, 200, 200), pixmap=pixmap)
    path = tmp_path / "scan.pdf"
    doc.save(path)
    doc.close()
    with pytest.raises(ValueError, match="no extractable text"):
        load_pdf_document(path)
def test_password_protected_pdf_is_rejected(tmp_path: Path) -> None:
    path = build_pdf(
        tmp_path / "locked.pdf",
        ["secret text"],
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        user_pw="user-pass",
        owner_pw="owner-pass",
    )
    with pytest.raises(ValueError, match="password-protected"):
        load_pdf_document(path)
def test_corrupt_pdf_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"this is not a pdf")
    with pytest.raises(ValueError, match="not a valid PDF"):
        load_pdf_document(path)
def test_zero_byte_pdf_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "zero.pdf"
    path.write_bytes(b"")
    with pytest.raises(ValueError):
        load_pdf_document(path)
def test_uppercase_extension_is_accepted(tmp_path: Path) -> None:
    path = build_pdf(tmp_path / "REPORT.PDF", ["upper case ext"])
    assert load_pdf_document(path).file_type == "pdf"
def test_unsupported_extension(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("not a pdf", encoding="utf-8")
    with pytest.raises(ValueError, match="Only .pdf files"):
        load_pdf_document(path)
def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_pdf_document(tmp_path / "missing.pdf")
def test_directory_instead_of_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Path is not a file"):
        load_pdf_document(tmp_path)
def test_document_id_is_content_based(tmp_path: Path) -> None:
    first = tmp_path / "a.pdf"
    second = tmp_path / "b.pdf"
    first.write_bytes(build_pdf(tmp_path / "src.pdf", ["same"]).read_bytes())
    second.write_bytes(first.read_bytes())
    assert load_pdf_document(first).document_id == load_pdf_document(second).document_id