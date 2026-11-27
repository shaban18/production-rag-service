"""Glue: document -> chunks -> embeddings -> Qdrant, and query -> hits."""
from app.chunking import chunk_document
from app.embeddings import Embedder
from app.ingestion.models import Document
from app.vector_store import SearchHit, VectorStore
def index_document(document: Document, store: VectorStore, embedder: Embedder) -> int:
    """Index a document, replacing any earlier version of the same file.
    Embedding happens before the old chunks are deleted, so a failure
    never leaves the document missing from the index.
    """
    chunks = chunk_document(document)
    vectors = embedder.embed([c.text for c in chunks])
    store.delete_document(document.document_id)
    store.upsert_chunks(chunks, vectors)
    return len(chunks)
def search_chunks(
    query: str, store: VectorStore, embedder: Embedder, top_k: int = 5
) -> list[SearchHit]:
    if not query.strip():
        raise ValueError("Query must not be blank")
    return store.search(embedder.embed_query(query), limit=top_k)