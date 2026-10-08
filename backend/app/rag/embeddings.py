"""Query-side embedding using a local all-MiniLM-L6-v2 model."""

from __future__ import annotations

import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load and cache the embedding model."""
    logger.info("Loading embedding model: %s", MODEL_NAME)
    return SentenceTransformer(MODEL_NAME)


def embed_query(text: str) -> list[float]:
    """Convert a user query into a normalized 384-dimensional embedding."""
    model = get_embedding_model()

    vector = model.encode(
        text[:4000],
        normalize_embeddings=True,
    ).tolist()

    if len(vector) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Unexpected embedding dimension: {len(vector)} "
            f"(expected {EMBEDDING_DIMENSION})"
        )

    return vector
