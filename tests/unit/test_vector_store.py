"""Tests for the Qdrant store and the indexing glue."""
import pytest
from app.indexing import index_document, search_chunks
from app.ingestion.models import Document, Page
from app.vector_store import VectorStore
def make_doc(doc_id="d1", pages=("apples are red fruit", "bananas are yellow fruit")):
    return Document(
        document_id=doc_id,
        source_filename=f"{doc_id}.pdf",
        file_type="pdf",
        pages=tuple(Page(page_number=i, text=t) for i, t in enumerate(pages, 1)),
    )
def test_index_and_search_returns_right_chunk_with_page(store, embedder):
    index_document(make_doc(), store, embedder)
    hits = search_chunks("yellow bananas", store, embedder, top_k=1)
    assert hits[0].chunk.page_number == 2
    assert hits[0].chunk.source_filename == "d1.pdf"
    assert "bananas" in hits[0].chunk.text
def test_reindexing_replaces_instead_of_duplicating(store, embedder):
    doc = make_doc()
    index_document(doc, store, embedder)
    index_document(doc, store, embedder)
    assert store.count_chunks("d1") == 2
def test_delete_document(store, embedder):
    index_document(make_doc("d1"), store, embedder)
    index_document(make_doc("d2"), store, embedder)
    assert store.delete_document("d1") == 2
    assert not store.has_document("d1")
    assert store.has_document("d2")
    assert store.delete_document("d1") == 0
def test_list_documents(store, embedder):
    index_document(make_doc("d1"), store, embedder)
    index_document(make_doc("d2"), store, embedder)
    docs = {d["document_id"]: d for d in store.list_documents()}
    assert set(docs) == {"d1", "d2"}
    assert docs["d1"]["chunk_count"] == 2
def test_search_on_empty_store_returns_nothing(store, embedder):
    assert search_chunks("anything", store, embedder) == []
def test_blank_query_is_rejected(store, embedder):
    with pytest.raises(ValueError):
        search_chunks("  ", store, embedder)
def test_wrong_dimension_vectors_are_rejected(store):
    with pytest.raises(ValueError):
        store.search([0.1, 0.2])
def test_data_persists_on_disk(tmp_path, embedder):
    path = str(tmp_path / "qdrant")
    first = VectorStore(embedder.dimension, path=path)
    index_document(make_doc(), first, embedder)
    first.close()
    second = VectorStore(embedder.dimension, path=path)
    try:
        assert second.has_document("d1")
        assert search_chunks("apples", second, embedder, top_k=1)[0].chunk.page_number == 1
    finally:
        second.close()