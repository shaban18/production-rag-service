"""PDF document loader (PyMuPDF).
Returns the shared page-aware ``Document``: one ``Page`` per PDF page,
numbered from 1 to match what a PDF viewer shows. Blank pages keep their
slot so later citations stay correct. PDFs with no extractable text
(scanned or image-only) are rejected, because this pipeline does not do OCR.
Errors follow the same contract as the TXT loader so the API layer can map
them to HTTP status codes later.
"""
import hashlib
from pathlib import Path
import pymupdf
from app.ingestion.models import Document, Page
SUPPORTED_EXTENSION = ".pdf"
def load_pdf_document(file_path: str | Path) -> Document:
    """Load a ``.pdf`` file as a page-aware ``Document``.
    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the path is not a file, the extension is not
            ``.pdf``, the file is not a readable PDF, the PDF is
            password-protected, or no page contains extractable text.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    if path.suffix.lower() != SUPPORTED_EXTENSION:
        raise ValueError("Only .pdf files are supported")
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise OSError(f"Unable to read file: {path}") from exc
    try:
        with pymupdf.open(stream=raw_bytes, filetype="pdf") as doc:
            if doc.needs_pass:
                raise ValueError(f"PDF is password-protected: {path}")
            texts = [page.get_text() for page in doc]
    except ValueError:
        raise
    except Exception as exc:  # PyMuPDF raises several error types
        raise ValueError(f"File is not a valid PDF: {path}") from exc
    if not texts:
        raise ValueError(f"PDF has no pages: {path}")
    if not any(text.strip() for text in texts):
        raise ValueError(
            "PDF has no extractable text (scanned or image-only PDFs "
            f"are not supported): {path}"
        )
    return Document(
        document_id=hashlib.sha256(raw_bytes).hexdigest(),
        source_filename=path.name,
        file_type="pdf",
        pages=tuple(
            Page(page_number=number, text=text)
            for number, text in enumerate(texts, start=1)
        ),
    )