"""Unified ingestion entry point.
``ingest_document`` picks the right loader from the file extension and
returns the shared page-aware ``Document``. Supporting a new format means
writing a loader and adding one line to ``LOADERS``.
"""
from collections.abc import Callable
from pathlib import Path
from app.ingestion.docx_loader import load_docx_document
from app.ingestion.loader import load_txt_document
from app.ingestion.models import Document
from app.ingestion.pdf_loader import load_pdf_document
LOADERS: dict[str, Callable[[Path], Document]] = {
    ".txt": load_txt_document,
    ".pdf": load_pdf_document,
    ".docx": load_docx_document,
}
def ingest_document(file_path: str | Path) -> Document:
    """Load a TXT, PDF or DOCX file as a ``Document``.
    Raises:
        ValueError: If the extension is unsupported, or if the chosen
            loader rejects the file.
        FileNotFoundError: If the path does not exist.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()
    loader = LOADERS.get(suffix)
    if loader is None:
        raise ValueError(f"Unsupported file type '{suffix or 'none'}'")
    return loader(path)