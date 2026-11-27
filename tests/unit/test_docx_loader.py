"""Unit tests for the DOCX loader. DOCX files are generated programmatically."""
import zipfile
from pathlib import Path
import docx
import pytest
from app.ingestion.docx_loader import load_docx_document
def build_docx(path: Path, paragraphs: list[str] | None = None) -> Path:
    word_doc = docx.Document()
    for text in paragraphs or []:
        word_doc.add_paragraph(text)
    word_doc.save(path)
    return path
def test_paragraphs_are_extracted(tmp_path: Path) -> None:
    path = build_docx(tmp_path / "p.docx", ["First paragraph", "Second paragraph"])
    document = load_docx_document(path)
    assert document.file_type == "docx"
    assert document.source_filename == "p.docx"
    assert len(document.pages) == 1
    assert document.pages[0].page_number == 1
    assert document.pages[0].text == "First paragraph\nSecond paragraph"
    assert len(document.document_id) == 64
def test_table_cells_are_extracted(tmp_path: Path) -> None:
    word_doc = docx.Document()
    word_doc.add_paragraph("Intro")
    table = word_doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Name"
    table.cell(0, 1).text = "Score"
    table.cell(1, 0).text = "Ali"
    table.cell(1, 1).text = "90"
    path = tmp_path / "t.docx"
    word_doc.save(path)
    text = load_docx_document(path).pages[0].text
    assert "Name | Score" in text
    assert "Ali | 90" in text
def test_document_order_is_preserved(tmp_path: Path) -> None:
    word_doc = docx.Document()
    word_doc.add_paragraph("before")
    table = word_doc.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "inside"
    word_doc.add_paragraph("after")
    path = tmp_path / "order.docx"
    word_doc.save(path)
    assert load_docx_document(path).pages[0].text == "before\ninside\nafter"
def test_merged_cells_are_not_duplicated(tmp_path: Path) -> None:
    word_doc = docx.Document()
    table = word_doc.add_table(rows=1, cols=3)
    merged = table.cell(0, 0).merge(table.cell(0, 1))
    merged.text = "Merged"
    table.cell(0, 2).text = "C"
    path = tmp_path / "merged.docx"
    word_doc.save(path)
    assert load_docx_document(path).pages[0].text == "Merged | C"
def test_table_only_document_is_accepted(tmp_path: Path) -> None:
    word_doc = docx.Document()
    table = word_doc.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "only table"
    path = tmp_path / "tableonly.docx"
    word_doc.save(path)
    assert "only table" in load_docx_document(path).pages[0].text
def test_page_numbers_are_marked_unavailable(tmp_path: Path) -> None:
    path = build_docx(tmp_path / "m.docx", ["text"])
    assert load_docx_document(path).metadata["page_numbers"] == "unavailable"
def test_document_without_text_is_rejected(tmp_path: Path) -> None:
    path = build_docx(tmp_path / "empty.docx", ["", "   "])
    with pytest.raises(ValueError, match="no extractable text"):
        load_docx_document(path)
def test_corrupt_docx_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "broken.docx"
    path.write_bytes(b"this is not a docx")
    with pytest.raises(ValueError, match="not a valid DOCX"):
        load_docx_document(path)
def test_zero_byte_docx_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "zero.docx"
    path.write_bytes(b"")
    with pytest.raises(ValueError):
        load_docx_document(path)
def test_zip_that_is_not_a_docx_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "fake.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("hello.txt", "just a zip")
    with pytest.raises(ValueError, match="not a valid DOCX"):
        load_docx_document(path)
def test_unsupported_extension(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("not a docx", encoding="utf-8")
    with pytest.raises(ValueError, match="Only .docx files"):
        load_docx_document(path)
def test_uppercase_extension_is_accepted(tmp_path: Path) -> None:
    path = build_docx(tmp_path / "REPORT.DOCX", ["upper"])
    assert load_docx_document(path).file_type == "docx"
def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_docx_document(tmp_path / "missing.docx")
def test_directory_instead_of_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Path is not a file"):
        load_docx_document(tmp_path)
def test_document_id_is_content_based(tmp_path: Path) -> None:
    first = build_docx(tmp_path / "a.docx", ["same"])
    second = tmp_path / "b.docx"
    second.write_bytes(first.read_bytes())
    assert load_docx_document(first).document_id == load_docx_document(second).document_id