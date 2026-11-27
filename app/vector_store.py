"""Qdrant vector store (local mode, cosine similarity)."""
from dataclasses import dataclass
from qdrant_client import QdrantClient, models
from app.chunking import Chunk
@dataclass(frozen=True)
class SearchHit:
    chunk: Chunk
    score: float
class VectorStore:
    """Pass ``path=None`` for an in-memory store (used in tests)."""
    def __init__(self, dimension: int, path: str | None = None, collection: str = "documents"):
        self.dimension = dimension
        self.collection = collection
        self._client = QdrantClient(path=path) if path else QdrantClient(":memory:")
        if not self._client.collection_exists(collection):
            self._client.create_collection(
                collection,
                vectors_config=models.VectorParams(
                    size=dimension, distance=models.Distance.COSINE
                ),
            )
    def close(self) -> None:
        self._client.close()
    @staticmethod
    def _doc_filter(document_id: str) -> models.Filter:
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id", match=models.MatchValue(value=document_id)
                )
            ]
        )
    def upsert_chunks(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Number of chunks and vectors differ")
        if any(len(v) != self.dimension for v in vectors):
            raise ValueError(f"Vectors must have {self.dimension} dimensions")
        if not chunks:
            return
        self._client.upsert(
            self.collection,
            points=[
                models.PointStruct(id=c.chunk_id, vector=v, payload=c.model_dump())
                for c, v in zip(chunks, vectors)
            ],
        )
    def count_chunks(self, document_id: str) -> int:
        return self._client.count(
            self.collection, count_filter=self._doc_filter(document_id), exact=True
        ).count
    def has_document(self, document_id: str) -> bool:
        return self.count_chunks(document_id) > 0
    def delete_document(self, document_id: str) -> int:
        removed = self.count_chunks(document_id)
        if removed:
            self._client.delete(
                self.collection,
                points_selector=models.FilterSelector(
                    filter=self._doc_filter(document_id)
                ),
            )
        return removed
    def list_documents(self) -> list[dict]:
        docs: dict[str, dict] = {}
        offset = None
        while True:
            points, offset = self._client.scroll(
                self.collection, limit=256, offset=offset,
                with_payload=True, with_vectors=False,
            )
            for p in points:
                entry = docs.setdefault(
                    p.payload["document_id"],
                    {
                        "document_id": p.payload["document_id"],
                        "source_filename": p.payload["source_filename"],
                        "file_type": p.payload["file_type"],
                        "chunk_count": 0,
                    },
                )
                entry["chunk_count"] += 1
            if offset is None:
                break
        return list(docs.values())
    def search(self, vector: list[float], limit: int = 5) -> list[SearchHit]:
        if len(vector) != self.dimension:
            raise ValueError(f"Query vector must have {self.dimension} dimensions")
        points = self._client.query_points(
            self.collection, query=vector, limit=limit, with_payload=True
        ).points
        return [SearchHit(chunk=Chunk(**p.payload), score=p.score) for p in points]