"""Unit tests for the shared Document model and load_txt_document."""
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.ingestion.loader import load_txt_document
from app.ingestion.models import Document, Page
def make_document(pages: tuple[Page, ...]) -> Document:
    return Document(
        document_id="abc",
        source_filename="x.pdf",
        file_type="pdf",
        pages=pages,
    )
@pytest.mark.parametrize("number", [0, -1])
def test_page_number_must_be_positive(number: int) -> None:
    with pytest.raises(ValidationError):
        Page(page_number=number, text="text")
@pytest.mark.parametrize("numbers", [[1, 3], [2, 3], [1, 1]])
def test_pages_must_be_consecutive_from_one(numbers: list[int]) -> None:
    pages = tuple(Page(page_number=n, text="text") for n in numbers)
    with pytest.raises(ValidationError, match="consecutive"):
        make_document(pages)
def test_document_requires_at_least_one_page() -> None:
    with pytest.raises(ValidationError):
        make_document(())
def test_document_rejects_when_all_pages_are_blank() -> None:
    pages = (Page(page_number=1, text=""), Page(page_number=2, text="  \n"))
    with pytest.raises(ValidationError, match="no extractable text"):
        make_document(pages)
def test_blank_page_in_the_middle_is_kept() -> None:
    pages = (
        Page(page_number=1, text="first"),
        Page(page_number=2, text=""),
        Page(page_number=3, text="third"),
    )
    document = make_document(pages)
    assert [p.page_number for p in document.pages] == [1, 2, 3]
def test_load_txt_document_builds_single_page_document(tmp_path: Path) -> None:
    file_path = tmp_path / "hello.txt"
    file_path.write_text("Hello RAG!", encoding="utf-8")
    document = load_txt_document(file_path)
    assert document.source_filename == "hello.txt"
    assert document.file_type == "txt"
    assert len(document.pages) == 1
    assert document.pages[0].page_number == 1
    assert document.pages[0].text == "Hello RAG!"
    assert len(document.document_id) == 64
def test_document_id_is_deterministic_and_content_based(tmp_path: Path) -> None:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    third = tmp_path / "c.txt"
    first.write_text("same content", encoding="utf-8")
    second.write_text("same content", encoding="utf-8")
    third.write_text("different content", encoding="utf-8")
    assert load_txt_document(first).document_id == load_txt_document(second).document_id
    assert load_txt_document(first).document_id != load_txt_document(third).document_id
def test_load_txt_document_propagates_loader_errors(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_txt_document(tmp_path / "missing.txt")