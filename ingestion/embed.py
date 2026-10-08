"""Document embedding using a local all-MiniLM-L6-v2 model.

The same embedding model is used during ingestion and query-time
retrieval so that document vectors and query vectors remain compatible.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from .config import EMBED_BATCH_SIZE

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load and cache the embedding model."""
    logger.info("Loading embedding model: %s", MODEL_NAME)
    return SentenceTransformer(MODEL_NAME)


def embed_local(
    texts: list[str],
    batch_size: int = EMBED_BATCH_SIZE,
) -> list[list[float]]:
    """Generate normalized embeddings for a list of text chunks."""
    if not texts:
        return []

    model = get_embedding_model()

    cleaned_texts = [text[:4000] for text in texts]

    vectors = model.encode(
        cleaned_texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    result = vectors.tolist()

    for index, vector in enumerate(result):
        if len(vector) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Unexpected embedding dimension for item {index}: "
                f"{len(vector)} (expected {EMBEDDING_DIMENSION})"
            )

    return result


class Embedder:
    """Batching wrapper used by the ingestion pipeline."""

    def __init__(self, batch_size: int = EMBED_BATCH_SIZE):
        self.batch_size = batch_size

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for all supplied texts."""
        if not texts:
            return []

        output: list[list[float]] = []

        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]

            logger.info(
                "Embedding batch %d-%d of %d",
                start + 1,
                min(start + len(batch), len(texts)),
                len(texts),
            )

            output.extend(
                embed_local(
                    batch,
                    batch_size=self.batch_size,
                )
            )

        return output