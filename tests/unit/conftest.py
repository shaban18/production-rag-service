"""Shared fixtures: a fast offline embedder and an in-memory store."""
import hashlib
import math
import re
import pytest
from app.vector_store import VectorStore
class FakeEmbedder:
    """Bag-of-words hashing embedder: similar words give similar vectors."""
    dimension = 64
    def embed(self, texts):
        out = []
        for text in texts:
            vec = [0.0] * self.dimension
            for word in re.findall(r"\w+", text.lower()):
                vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dimension] += 1
            norm = math.sqrt(sum(x * x for x in vec))
            if norm == 0:
                raise ValueError("Cannot embed blank text")
            out.append([x / norm for x in vec])
        return out
    def embed_query(self, query):
        return self.embed([query])[0]
@pytest.fixture
def embedder():
    return FakeEmbedder()
@pytest.fixture
def store(embedder):
    s = VectorStore(dimension=embedder.dimension)
    yield s
    s.close()