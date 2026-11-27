"""Unit tests for the TXT document loader."""

from pathlib import Path

import pytest

from app.ingestion.loader import load_text_file


def test_load_valid_txt_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Hello RAG!", encoding="utf-8")

    assert load_text_file(file_path) == "Hello RAG!"


def test_load_preserves_multiline_and_unicode_text(tmp_path: Path) -> None:
    # \u0633\u0637\u0631 is Urdu text; \u00e9 is an accented letter.
    text = "Line one\nCaf\u00e9\n\u0633\u0637\u0631 \u062f\u0648\u0645"
    file_path = tmp_path / "unicode.txt"
    file_path.write_bytes(text.encode("utf-8"))

    assert load_text_file(file_path) == text


def test_bom_is_stripped(tmp_path: Path) -> None:
    file_path = tmp_path / "bom.txt"
    file_path.write_bytes(b"\xef\xbb\xbfHello")

    result = load_text_file(file_path)

    assert result == "Hello"
    assert not result.startswith("\ufeff")


def test_uppercase_extension_is_accepted(tmp_path: Path) -> None:
    file_path = tmp_path / "NOTES.TXT"
    file_path.write_text("Some notes", encoding="utf-8")

    assert load_text_file(file_path) == "Some notes"


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_text_file(tmp_path / "missing.txt")


def test_empty_file(tmp_path: Path) -> None:
    file_path = tmp_path / "empty.txt"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="File is empty"):
        load_text_file(file_path)


@pytest.mark.parametrize("content", ["   ", "\n\n", "\t \n "])
def test_whitespace_only_file_is_empty(tmp_path: Path, content: str) -> None:
    file_path = tmp_path / "blank.txt"
    file_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="File is empty"):
        load_text_file(file_path)


def test_unsupported_extension(tmp_path: Path) -> None:
    file_path = tmp_path / "document.pdf"
    file_path.write_text("Some content", encoding="utf-8")

    with pytest.raises(ValueError, match="Only .txt files"):
        load_text_file(file_path)


def test_directory_instead_of_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Path is not a file"):
        load_text_file(tmp_path)


def test_invalid_utf8_file(tmp_path: Path) -> None:
    file_path = tmp_path / "invalid.txt"
    file_path.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(ValueError, match="valid UTF-8"):
        load_text_file(file_path)