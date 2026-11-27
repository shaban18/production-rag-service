"""Upload validation: extension allow-list, size limit, safe filenames.
``validate_upload`` is meant to run on the raw upload (filename and size)
before anything is written to disk, so a hostile filename can never reach
the file system.
"""
import re
from pathlib import Path
from app.config import settings
ALLOWED_EXTENSIONS = frozenset({".txt", ".pdf", ".docx"})
MAX_FILENAME_LENGTH = 100
_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
_UNSAFE_CHARS = re.compile(r'[<>:"|?*\x00-\x1f\x7f]')
def sanitize_filename(filename: str) -> str:
    """Return a safe bare filename.
    Strips any directory part (both ``/`` and ``\\`` separators), removes
    control and Windows-reserved characters, trims leading and trailing
    spaces and dots, rejects Windows reserved device names (CON, NUL, ...)
    and caps the length while keeping the extension.
    Raises:
        ValueError: If nothing usable is left or the name is reserved.
    """
    name = re.split(r"[\\/]", filename)[-1]
    name = _UNSAFE_CHARS.sub("", name)
    name = name.strip(" .")
    if not name:
        raise ValueError("Filename is empty or unsafe")
    if name.split(".")[0].upper() in _RESERVED_NAMES:
        raise ValueError(f"Filename uses a reserved name: {name}")
    if len(name) > MAX_FILENAME_LENGTH:
        suffix = Path(name).suffix
        if len(suffix) > 10:
            name = name[:MAX_FILENAME_LENGTH]
        else:
            name = name[: MAX_FILENAME_LENGTH - len(suffix)] + suffix
    return name
def validate_upload(
    filename: str, size_bytes: int, max_bytes: int | None = None
) -> str:
    """Validate an upload and return its sanitized filename.
    Raises:
        ValueError: If the filename is unsafe, the extension is not in the
            allow-list, the file is empty, or it exceeds the size limit.
    """
    safe_name = sanitize_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(
            f"Unsupported file type '{suffix or 'none'}'. Allowed: {allowed}"
        )
    if size_bytes <= 0:
        raise ValueError("Uploaded file is empty")
    limit = settings.MAX_UPLOAD_BYTES if max_bytes is None else max_bytes
    if size_bytes > limit:
        raise ValueError(f"File exceeds the maximum size of {limit} bytes")
    return safe_name