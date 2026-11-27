"""DOCX document loader (python-docx).
Returns the shared ``Document`` as a single page. A DOCX file has no fixed
pages: pagination is computed by Word at render time and cannot be
reproduced here, so inventing page numbers would produce wrong citations.
``metadata["page_numbers"] == "unavailable"`` tells the citation layer to
cite the file without a page.
Paragraphs and tables are extracted in document order. Table rows become
lines with cells joined by " | ". Nested tables, headers, footers, text
boxes and images are not extracted.
Errors follow the same contract as the TXT and PDF loaders.
"""
import hashlib
import io
from pathlib import Path
import docx
from app.ingestion.models import Document, Page
SUPPORTED_EXTENSION = ".docx"
def _table_lines(table) -> list[str]:
    lines: list[str] = []
    for row in table.rows:
        cells = []
        seen = set()
        for cell in row.cells:
            # Merged cells appear several times in row.cells; keep one.
            if id(cell._tc) in seen:
                continue
            seen.add(id(cell._tc))
            cells.append(cell.text.strip())
        if any(cells):
            lines.append(" | ".join(cells))
    return lines
def load_docx_document(file_path: str | Path) -> Document:
    """Load a ``.docx`` file as a single-page ``Document``.
    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the path is not a file, the extension is not
            ``.docx``, the file is not a readable DOCX, or it contains
            no text.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    if path.suffix.lower() != SUPPORTED_EXTENSION:
        raise ValueError("Only .docx files are supported")
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise OSError(f"Unable to read file: {path}") from exc
    try:
        word_doc = docx.Document(io.BytesIO(raw_bytes))
        blocks: list[str] = []
        for item in word_doc.iter_inner_content():
            if isinstance(item, docx.text.paragraph.Paragraph):
                if item.text.strip():
                    blocks.append(item.text)
            else:
                blocks.extend(_table_lines(item))
    except Exception as exc:  # python-docx raises several error types
        raise ValueError(f"File is not a valid DOCX: {path}") from exc
    text = "\n".join(blocks)
    if not text.strip():
        raise ValueError(f"DOCX has no extractable text: {path}")
    return Document(
        document_id=hashlib.sha256(raw_bytes).hexdigest(),
        source_filename=path.name,
        file_type="docx",
        pages=(Page(page_number=1, text=text),),
        metadata={"page_numbers": "unavailable"},
    )