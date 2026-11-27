
from pathlib import Path

import pytest

from app.ingestion.loader import load_text_file


def test_load_valid_txt_file(tmp_path: Path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Hello RAG!", encoding="utf-8")

    result = load_text_file(file_path)

    assert result == "Hello RAG!"


def test_missing_file():
    with pytest.raises(FileNotFoundError):
        load_text_file("data/corpus/missing.txt")


def test_empty_file(tmp_path: Path):
    file_path = tmp_path / "empty.txt"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="File is empty"):
        load_text_file(file_path)


def test_unsupported_extension(tmp_path: Path):
    file_path = tmp_path / "document.pdf"
    file_path.write_text("Some content", encoding="utf-8")

    with pytest.raises(ValueError, match="Only .txt files"):
        load_text_file(file_path)


def test_directory_instead_of_file(tmp_path: Path):
    with pytest.raises(ValueError, match="Path is not a file"):
        load_text_file(tmp_path)


def test_invalid_utf8_file(tmp_path: Path):
    file_path = tmp_path / "invalid.txt"
    file_path.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(ValueError, match="valid UTF-8"):
        load_text_file(file_path)
