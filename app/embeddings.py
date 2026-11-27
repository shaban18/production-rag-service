"""Embedding generation (BAAI/bge-small-en-v1.5 via fastembed, local ONNX)."""
from typing import Protocol
from app.config import settings
class Embedder(Protocol):
    dimension: int
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, query: str) -> list[float]: ...
class FastEmbedEmbedder:
    """Loads the model lazily on first use."""
    def __init__(self, model_name: str | None = None, dimension: int | None = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.dimension = dimension or settings.EMBEDDING_DIMENSION
        self._model = None
    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model
    def _check(self, vector: list[float]) -> list[float]:
        if len(vector) != self.dimension:
            raise ValueError(
                f"Embedding has {len(vector)} dimensions, expected {self.dimension}"
            )
        return vector
    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not t.strip() for t in texts):
            raise ValueError("Cannot embed blank text")
        model = self._load()
        return [self._check(v.tolist()) for v in model.embed(texts, batch_size=32)]
    def embed_query(self, query: str) -> list[float]:
        if not query.strip():
            raise ValueError("Cannot embed a blank query")
        model = self._load()
        return self._check(next(iter(model.query_embed(query))).tolist())