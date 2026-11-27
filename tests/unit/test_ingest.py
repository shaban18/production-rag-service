"""Unit tests for the unified ingest_document entry point."""
from pathlib import Path
import docx
import pymupdf
import pytest
from app.ingestion.ingest import LOADERS, ingest_document
from app.ingestion.validation import ALLOWED_EXTENSIONS
def test_txt_is_routed_to_txt_loader(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("hello txt", encoding="utf-8")
    document = ingest_document(path)
    assert document.file_type == "txt"
    assert document.pages[0].text == "hello txt"
def test_pdf_is_routed_to_pdf_loader(tmp_path: Path) -> None:
    path = tmp_path / "a.pdf"
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "hello pdf")
    pdf.save(path)
    pdf.close()
    document = ingest_document(path)
    assert document.file_type == "pdf"
    assert "hello pdf" in document.pages[0].text
def test_docx_is_routed_to_docx_loader(tmp_path: Path) -> None:
    path = tmp_path / "a.docx"
    word_doc = docx.Document()
    word_doc.add_paragraph("hello docx")
    word_doc.save(path)
    document = ingest_document(path)
    assert document.file_type == "docx"
    assert document.pages[0].text == "hello docx"
def test_extension_matching_is_case_insensitive(tmp_path: Path) -> None:
    path = tmp_path / "NOTES.TXT"
    path.write_text("upper", encoding="utf-8")
    assert ingest_document(path).file_type == "txt"
@pytest.mark.parametrize("name", ["a.exe", "noext"])
def test_unsupported_type_is_rejected(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError, match="Unsupported file type"):
        ingest_document(tmp_path / name)
def test_missing_supported_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ingest_document(tmp_path / "missing.txt")
def test_loader_errors_propagate(tmp_path: Path) -> None:
    path = tmp_path / "zero.pdf"
    path.write_bytes(b"")
    with pytest.raises(ValueError):
        ingest_document(path)
def test_registry_matches_validation_allow_list() -> None:
    assert set(LOADERS) == set(ALLOWED_EXTENSIONS)