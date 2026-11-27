"""Page-aware chunking.
Chunks never span pages, so every chunk keeps an exact page number for
citations. For formats without real pages (DOCX) ``page_number`` is None.
"""
import re
import uuid
from pydantic import BaseModel, ConfigDict
from app.config import settings
from app.ingestion.models import Document
class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True)
    chunk_id: str
    document_id: str
    source_filename: str
    file_type: str
    page_number: int | None
    chunk_index: int
    text: str
def split_text(text: str, size: int, overlap: int) -> list[str]:
    """Split text into windows of at most ``size`` characters.
    Breaks at whitespace where possible; consecutive chunks share about
    ``overlap`` characters.
    """
    if size <= 0:
        raise ValueError("Chunk size must be positive")
    if not 0 <= overlap < size:
        raise ValueError("Overlap must be >= 0 and smaller than chunk size")
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            window = text[start:end]
            cut = max(window.rfind("\n"), window.rfind(" "))
            if cut > size // 2:
                end = start + cut
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
        if start > 0 and not text[start - 1].isspace():
            match = re.search(r"\s", text[start:end])
            if match:
                start += match.end()
    return chunks
def chunk_document(
    document: Document, chunk_size: int | None = None, overlap: int | None = None
) -> list[Chunk]:
    size = settings.CHUNK_SIZE if chunk_size is None else chunk_size
    ovl = settings.CHUNK_OVERLAP if overlap is None else overlap
    has_pages = document.metadata.get("page_numbers") != "unavailable"
    chunks: list[Chunk] = []
    for page in document.pages:
        for piece in split_text(page.text, size, ovl):
            index = len(chunks)
            chunks.append(
                Chunk(
                    chunk_id=str(
                        uuid.uuid5(uuid.NAMESPACE_URL, f"{document.document_id}:{index}")
                    ),
                    document_id=document.document_id,
                    source_filename=document.source_filename,
                    file_type=document.file_type,
                    page_number=page.page_number if has_pages else None,
                    chunk_index=index,
                    text=piece,
                )
            )
    return chunks