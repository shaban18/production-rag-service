"""Plain-text (.txt) document loader.

Reads a UTF-8 text file from disk and returns its content as a string.
Problems are reported with explicit exceptions so that callers (the
ingestion pipeline and, later, the API layer) can translate them into
the right HTTP status codes.
"""

from pathlib import Path

SUPPORTED_EXTENSION = ".txt"


def load_text_file(file_path: str | Path) -> str:
    """Load a UTF-8 text file and return its content.

    A leading byte-order mark (BOM), which some Windows editors add when
    saving "UTF-8" files, is removed so it never ends up in the text.

    Args:
        file_path: Path to a ``.txt`` file (the extension check is
            case-insensitive).

    Returns:
        The full text content of the file.

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the path is not a file, the extension is not
            ``.txt``, the bytes are not valid UTF-8, or the file has no
            text other than whitespace.
        OSError: If the file exists but cannot be read.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    if path.suffix.lower() != SUPPORTED_EXTENSION:
        raise ValueError("Only .txt files are supported")

    try:
        # "utf-8-sig" decodes normal UTF-8 and drops a leading BOM if present.
        content = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"File does not contain valid UTF-8 text: {path}"
        ) from exc
    except OSError as exc:
        raise OSError(f"Unable to read file: {path}") from exc

    if not content.strip():
        raise ValueError(f"File is empty: {path}")

    return content