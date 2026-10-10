"""Document embedding using a local all-MiniLM-L6-v2 model.

Powered by fastembed (ONNX runtime) to remain 100% compatible with
existing Supabase vectors while eliminating PyTorch memory overhead.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from fastembed import TextEmbedding

from .config import EMBED_BATCH_SIZE

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
  """Load and cache the embedding model."""
  logger.info("Loading embedding model: %s", MODEL_NAME)
  return TextEmbedding(model_name=MODEL_NAME)


def embed_local(
    texts: list[str],
    batch_size: int = EMBED_BATCH_SIZE,
) -> list[list[float]]:
  """Generate normalized embeddings for a list of text chunks."""
  if not texts:
    return []

  model = get_embedding_model()
  cleaned_texts = [text[:4000] for text in texts]

  # fastembed handles batching and returns normalized embeddings by default
  embeddings_gen = model.embed(cleaned_texts, batch_size=batch_size)
  result = [v.tolist() for v in embeddings_gen]

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