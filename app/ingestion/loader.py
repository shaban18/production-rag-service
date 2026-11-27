
from pathlib import Path


def load_text_file(file_path: str | Path) -> str:
    """
    Load a UTF-8 text file and return its content.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the path is invalid, extension is unsupported,
                    content is empty, or encoding is invalid.
        OSError: If the file cannot be read.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    if path.suffix.lower() != ".txt":
        raise ValueError("Only .txt files are supported")

    try:
        content = path.read_text(encoding="utf-8")

    except UnicodeDecodeError as exc:
        raise ValueError(
            f"File does not contain valid UTF-8 text: {path}"
        ) from exc

    except OSError as exc:
        raise OSError(f"Unable to read file: {path}") from exc

    if not content.strip():
        raise ValueError(f"File is empty: {path}")

    return content
