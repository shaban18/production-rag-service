"""Shared, page-aware representation of an extracted document.

Every loader (TXT now, PDF and DOCX later) returns a ``Document`` so the
rest of the RAG pipeline never needs to know which file format it came
from. Page numbers are 1-based so citations match what a reader sees.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FileType = Literal["txt", "pdf", "docx"]


class Page(BaseModel):
    """Text extracted from one page of a document.

    ``text`` may be empty: a blank page in the middle of a PDF must still
    occupy its page number so later citations stay correct.
    """

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    text: str


class Document(BaseModel):
    """An extracted document: identity, source information and pages."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    source_filename: str
    file_type: FileType
    pages: tuple[Page, ...] = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_pages(self) -> "Document":
        numbers = [page.page_number for page in self.pages]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("Page numbers must be consecutive and start at 1")
        if not any(page.text.strip() for page in self.pages):
            raise ValueError("Document has no extractable text")
        return self
        