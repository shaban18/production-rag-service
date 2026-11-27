# Design Decisions
This file records significant engineering decisions: what was chosen, why,
which alternatives were considered, and the trade-offs accepted.
## 1. Shared page-aware document model
**Decision.** Every loader returns the same `Document` (Pydantic v2, in
`app/ingestion/models.py`). A `Document` has a `document_id`,
`source_filename`, `file_type`, `metadata` and a tuple of `Page` objects.
Each `Page` has a 1-based `page_number` and its `text`.
**Why.** Citations must point to a page. Returning one string, as the first
TXT loader did, loses page boundaries. A shared shape lets later stages
(chunking, embedding, retrieval) ignore the source format, so adding DOCX
needs no pipeline changes.
**Rules enforced by the model.**
- Page numbers are 1-based and consecutive, matching a PDF viewer.
- A `Page` may be blank. Dropping blank pages would shift every later page
  number and corrupt citations.
- A `Document` must contain some non-whitespace text. This rejects
  image-only documents at the model level as a second line of defence.
- `document_id` is the SHA-256 of the raw file bytes. The same file always
  gets the same ID, which supports duplicate handling when documents are
  indexed. It identifies the file, not its text, so a UTF-8 BOM copy of
  the same text gets a different ID.
**Compatibility.** `load_text_file` still returns a `str` so existing
callers and tests are unchanged. `load_txt_document` wraps it in a
single-page `Document`.
## 2. PDF extraction library
**Decision.** PyMuPDF (`import pymupdf`), via `app/ingestion/pdf_loader.py`.
**Alternatives considered.**
| Library | Notes |
| --- | --- |
| PyMuPDF | Fast, page-by-page extraction, good reading order on complex layouts such as two-column papers. AGPL-3.0 or commercial licence. |
| pypdf | Pure Python, permissive licence (BSD). Text extraction is generally weaker on complex layouts. |
| pdfplumber | Strong for tables and layout analysis. Slower, and more than needed for plain text extraction. |
**Why PyMuPDF.** Extraction quality and speed on research-style PDFs, and
straightforward detection of pages with no extractable text.
**Licensing trade-off.** PyMuPDF is dual licensed: GNU AGPL-3.0 or an
Artifex commercial licence. This is a real constraint. The AGPL has strong
copyleft terms that can apply to software offered to users over a network.
For a portfolio and learning project this is acceptable. Before any
commercial or closed-source deployment, either obtain a commercial licence
or replace PyMuPDF. pypdf is the permissively licensed fallback, and it
would only require swapping `pdf_loader.py` because the rest of the
pipeline depends on the shared `Document` model, not on PyMuPDF.
## 3. PDF loader behaviour
- One `Page` per PDF page, numbered from 1. Blank pages keep their slot.
- The file is read once. The hash and the extracted text come from the same
  bytes.
- **Image-only and scanned PDFs are rejected** with a `ValueError`
  ("no extractable text"). They are never ingested silently. OCR is out of
  scope for this pipeline. Silent ingestion would produce an index that
  looks healthy but has nothing to retrieve.
- Password-protected, corrupt and zero-byte files are rejected with a
  `ValueError`.
- Errors follow the TXT loader's contract: `FileNotFoundError` for a missing
  path, `ValueError` for invalid input, so the API layer can map them to
  HTTP status codes later.
## 4. Dependency footprint
Installing PyMuPDF 2.2 also pulled in `pymupdf_layout`, `pymupdf4llm`,
`numpy`, `onnxruntime`, `networkx`, `psutil`, `PyYAML` and `tabulate`.
`pip show` reports a circular requirement among `pymupdf`,
`pymupdf_layout` and `pymupdf4llm`. All are pinned in `requirements.txt` so
the environment is reproducible. The loader only uses `page.get_text()`.
**Open item:** test whether a leaner install works in a throwaway virtual
environment before the embedding phase adds its own heavy dependencies.
## 5. Known gaps
- No Urdu or other non-Latin PDF test yet. It needs an embedded font in the
  generated test PDF. Accented Latin text is tested.
- No DOCX loader yet.