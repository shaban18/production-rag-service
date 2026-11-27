"""Tests for embedding helpers (the real model is covered by the smoke test)."""
import pytest
from app.embeddings import FastEmbedEmbedder
def test_empty_input_returns_empty_list_without_loading_model():
    assert FastEmbedEmbedder().embed([]) == []
def test_blank_text_is_rejected_without_loading_model():
    with pytest.raises(ValueError):
        FastEmbedEmbedder().embed(["ok", "  "])
    with pytest.raises(ValueError):
        FastEmbedEmbedder().embed_query(" ")
def test_fake_embedder_vectors_have_declared_dimension(embedder):
    vectors = embedder.embed(["one two", "three"])
    assert all(len(v) == embedder.dimension for v in vectors)