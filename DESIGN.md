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
## 5. DOCX extraction
**Decision.** `python-docx` (MIT licence), via `app/ingestion/docx_loader.py`.
A DOCX becomes a **single-page** `Document`, with
`metadata["page_numbers"] == "unavailable"`.
**Why single page.** A DOCX file has no fixed pages. Word computes
pagination at render time and `python-docx` cannot reproduce it. Splitting on
manual page breaks would miss automatic breaks, so the numbers would not match
what Word shows. Wrong page citations are worse than none, so the citation
layer must cite DOCX sources by filename only.
**Extraction rules.**
- Paragraphs and tables are extracted in document order.
- Table rows become lines, with cells joined by " | ".
- Merged cells are de-duplicated (python-docx repeats them per column).
- Not extracted: nested tables, headers and footers, text boxes, images.
- Corrupt files, zero-byte files, ZIP archives that are not DOCX files and
  documents with no text are rejected with a `ValueError`.
## 6. Upload validation and unified ingestion
**Validation** (`app/ingestion/validation.py`) runs on the raw filename and
size, before anything is written to disk.
- Extension allow-list: `.txt`, `.pdf`, `.docx`, case-insensitive.
- Size limit: `MAX_UPLOAD_BYTES` in settings, default 10 MB, overridable via
  `.env`. Zero-byte uploads are rejected.
- `sanitize_filename` strips directory parts (both `/` and `\`), removes
  control and Windows-reserved characters, trims spaces and dots, rejects
  reserved device names (CON, NUL, COM1, ...) and caps the length while
  keeping the extension. This prevents path traversal.
- Extension checks look at the file name only. Content is verified by the
  loaders, which reject files that are not really a PDF or DOCX.
**Unified ingestion** (`app/ingestion/ingest.py`). `ingest_document(path)`
picks the loader from a `LOADERS` registry keyed by extension. A new format
is one loader plus one registry line. A test asserts that the registry and
the validation allow-list list the same extensions.
## 7. Known gaps
- No Urdu or other non-Latin PDF test yet. It needs an embedded font in the
  generated test PDF. Accented Latin text is tested.
- Whether the heavy PyMuPDF dependencies can be trimmed is untested.
- `validate_upload` and `ingest_document` are not yet wired into an API
  endpoint.
- No OCR for scanned PDFs (by design, they are rejected).
## 8. Chunking, embeddings and vector storage
- **Chunking** (`app/chunking.py`): character windows (default 1000, overlap
  200, configurable), broken at whitespace. Chunks never span pages, so each
  keeps an exact `page_number` (None for DOCX). Chunk IDs are deterministic
  UUIDs from document ID and index.
- **Embeddings** (`app/embeddings.py`): `BAAI/bge-small-en-v1.5` (384 dims)
  through `fastembed` (ONNX, reuses `onnxruntime`) instead of
  `sentence-transformers`, which would add PyTorch (~2 GB). Dimension is
  validated; blank text is rejected. BGE-M3 comparison is still open.
- **Vector store** (`app/vector_store.py`): Qdrant local mode, cosine
  distance, persisted in `data/qdrant` (git-ignored). Re-indexing a document
  replaces its chunks (embedding runs first, so a failure keeps the old
  data). Identical files share a `document_id`, so duplicates collapse.
- **Open:** chunk size and overlap are defaults, not yet tuned by evaluation.
## 9. Retrieval threshold and grounded answering
- **Flow** (`app/qa.py`): embed question, search Qdrant, drop chunks below
  `MIN_RELEVANCE_SCORE`, ask Gemini (`GEMINI_MODEL`, default
  `gemini-3.8-flash`) with only those excerpts, validate the reply.
- **Refusal** happens without calling the model when nothing passes the
  threshold, and after the call when the model says the evidence is
  insufficient, returns malformed output, or cites no retrieved excerpt.
- **Citations** are excerpt numbers checked against the retrieved set, then
  mapped to filename, page (None for DOCX) and chunk. Invalid numbers are
  dropped. Limitation: this proves a citation points at a retrieved chunk,
  not that the chunk truly supports the claim. Evaluation must measure that.
- **Prompt injection:** excerpts are wrapped in tags and declared untrusted
  data; closing tags inside document text are escaped. This reduces but does
  not eliminate the risk.
- **Failures:** HTTP 429 and 5xx from Gemini are retried with exponential
  backoff, then raised as `LLMError`.
- **Open:** `MIN_RELEVANCE_SCORE` (0.5), `TOP_K` (5), and the free-tier rate
  limits are untuned defaults. The threshold must be set from evaluation data.
  No BM25, hybrid retrieval or reranking yet.
