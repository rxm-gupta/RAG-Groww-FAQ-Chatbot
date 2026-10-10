"""Query-side embedding using a lightweight local all-MiniLM-L6-v2 model.

Powered by fastembed (ONNX runtime) to run within Render's 512 MB memory limit.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
  """Load and cache the embedding model using ONNX runtime (~120 MB RAM)."""
  logger.info("Loading lightweight embedding model: %s", MODEL_NAME)
  return TextEmbedding(model_name=MODEL_NAME)


def embed_query(text: str) -> list[float]:
  """Convert a user query into a normalized 384-dimensional embedding."""
  model = get_embedding_model()

  # fastembed.embed takes an iterable and yields numpy arrays
  embedding_gen = model.embed([text[:4000]])
  vector = list(embedding_gen)[0].tolist()

  if len(vector) != EMBEDDING_DIMENSION:
    raise ValueError(
        f"Unexpected embedding dimension: {len(vector)} "
        f"(expected {EMBEDDING_DIMENSION})"
    )

  return vector