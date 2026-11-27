"""Tests for page-aware chunking."""
import pytest
from app.chunking import chunk_document, split_text
from app.ingestion.models import Document, Page
def make_doc(texts, metadata=None, file_type="pdf"):
    return Document(
        document_id="doc1",
        source_filename="f." + file_type,
        file_type=file_type,
        pages=tuple(Page(page_number=i, text=t) for i, t in enumerate(texts, 1)),
        metadata=metadata or {},
    )
def test_short_page_is_one_chunk():
    chunks = chunk_document(make_doc(["hello world"]), 100, 10)
    assert [c.text for c in chunks] == ["hello world"]
    assert chunks[0].page_number == 1
def test_long_text_is_split_within_size_and_overlaps():
    text = " ".join(f"word{i}" for i in range(300))
    pieces = split_text(text, 200, 40)
    assert len(pieces) > 1
    assert all(len(p) <= 200 for p in pieces)
    assert set(pieces[0].split()) & set(pieces[1].split())
    assert " ".join(pieces[-1].split()[-1:]) == "word299"
def test_no_words_are_lost():
    text = " ".join(f"w{i}" for i in range(500))
    pieces = split_text(text, 150, 30)
    assert {w for p in pieces for w in p.split()} == set(text.split())
def test_chunks_never_span_pages():
    chunks = chunk_document(make_doc(["alpha " * 10, "bravo " * 10]), 40, 5)
    assert {c.page_number for c in chunks} == {1, 2}
    assert all("alpha" not in c.text for c in chunks if c.page_number == 2)
    assert all("bravo" not in c.text for c in chunks if c.page_number == 1)
def test_blank_pages_are_skipped_but_numbers_kept():
    chunks = chunk_document(make_doc(["first", "", "third"]), 100, 10)
    assert [c.page_number for c in chunks] == [1, 3]
def test_docx_chunks_have_no_page_number():
    doc = make_doc(["text"], {"page_numbers": "unavailable"}, "docx")
    assert chunk_document(doc, 100, 10)[0].page_number is None
def test_chunk_ids_are_deterministic_and_unique():
    doc = make_doc(["word " * 100])
    a = chunk_document(doc, 50, 10)
    b = chunk_document(doc, 50, 10)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
    assert len({c.chunk_id for c in a}) == len(a)
    assert [c.chunk_index for c in a] == list(range(len(a)))
@pytest.mark.parametrize("size,overlap", [(0, 0), (10, 10), (10, -1), (10, 20)])
def test_invalid_parameters_are_rejected(size, overlap):
    with pytest.raises(ValueError):
        split_text("some text", size, overlap)
def test_unbroken_text_still_terminates():
    pieces = split_text("x" * 1000, 100, 20)
    assert len(pieces) >= 10 and all(len(p) <= 100 for p in pieces)