"""Unit tests for upload validation and filename sanitizing."""
import pytest
from app.config import settings
from app.ingestion.validation import (
    MAX_FILENAME_LENGTH,
    sanitize_filename,
    validate_upload,
)
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("..\\..\\evil.pdf", "evil.pdf"),
        ("../../etc/passwd.txt", "passwd.txt"),
        ("C:\\Users\\x\\report.docx", "report.docx"),
        ("/tmp/notes.txt", "notes.txt"),
    ],
)
def test_directory_components_are_stripped(raw: str, expected: str) -> None:
    assert sanitize_filename(raw) == expected
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("re<po>rt?.pdf", "report.pdf"),
        ("a\x00b\x1f.txt", "ab.txt"),
        ('na:me|x*.txt', "namex.txt"),
    ],
)
def test_unsafe_characters_are_removed(raw: str, expected: str) -> None:
    assert sanitize_filename(raw) == expected
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  report.pdf  ", "report.pdf"),
        ("...report.pdf", "report.pdf"),
        ("report.pdf.", "report.pdf"),
    ],
)
def test_leading_and_trailing_spaces_and_dots_are_trimmed(
    raw: str, expected: str
) -> None:
    assert sanitize_filename(raw) == expected
@pytest.mark.parametrize(
    "name", ["report.pdf", "caf\u00e9.txt", "\u0631\u067e\u0648\u0631\u0679.docx"]
)
def test_normal_and_unicode_names_are_kept(name: str) -> None:
    assert sanitize_filename(name) == name
@pytest.mark.parametrize("raw", ["", "   ", "..", "...", "a/", "\\", "<>:"])
def test_empty_or_unsafe_names_are_rejected(raw: str) -> None:
    with pytest.raises(ValueError, match="Filename"):
        sanitize_filename(raw)
@pytest.mark.parametrize(
    "raw", ["CON", "con.txt", "NUL.pdf", "COM1.docx", "lpt9.txt", "aux.tar.txt"]
)
def test_windows_reserved_names_are_rejected(raw: str) -> None:
    with pytest.raises(ValueError, match="reserved"):
        sanitize_filename(raw)
def test_names_that_only_start_like_reserved_names_are_fine() -> None:
    assert sanitize_filename("console.txt") == "console.txt"
    assert sanitize_filename("communication.txt") == "communication.txt"
def test_long_names_are_capped_and_keep_extension() -> None:
    result = sanitize_filename("a" * 300 + ".pdf")
    assert len(result) <= MAX_FILENAME_LENGTH
    assert result.endswith(".pdf")
@pytest.mark.parametrize("name", ["a.txt", "b.PDF", "c.Docx"])
def test_allowed_extensions_pass_case_insensitively(name: str) -> None:
    assert validate_upload(name, 100) == name
@pytest.mark.parametrize("name", ["a.exe", "a.doc", "a", "a.pdf.exe", "a.txt.sh"])
def test_unsupported_extensions_are_rejected(name: str) -> None:
    with pytest.raises(ValueError, match="Unsupported file type"):
        validate_upload(name, 100)
@pytest.mark.parametrize("size", [0, -1])
def test_empty_upload_is_rejected(size: int) -> None:
    with pytest.raises(ValueError, match="empty"):
        validate_upload("a.txt", size)
def test_oversized_upload_is_rejected() -> None:
    with pytest.raises(ValueError, match="maximum size"):
        validate_upload("a.txt", 11, max_bytes=10)
def test_upload_at_exact_limit_is_accepted() -> None:
    assert validate_upload("a.txt", 10, max_bytes=10) == "a.txt"
def test_default_limit_comes_from_settings() -> None:
    assert validate_upload("a.txt", settings.MAX_UPLOAD_BYTES) == "a.txt"
    with pytest.raises(ValueError, match="maximum size"):
        validate_upload("a.txt", settings.MAX_UPLOAD_BYTES + 1)
def test_validate_upload_returns_sanitized_name() -> None:
    assert validate_upload("..\\..\\evil.pdf", 5) == "evil.pdf"