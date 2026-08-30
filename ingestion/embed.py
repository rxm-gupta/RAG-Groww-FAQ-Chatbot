"""Embedding client: Hugging Face Inference API only (all-MiniLM-L6-v2, 384-dim).

No local model is used or installed. If the API is unavailable, callers
receive an exception and the application returns its standard error message.
"""
from __future__ import annotations

import logging
import time

import httpx

from .config import EMBED_BATCH_SIZE, HF_API_KEY, HF_INFERENCE_URL

logger = logging.getLogger(__name__)


def embed_hf(texts: list[str], retries: int = 3, timeout: float = 60.0) -> list[list[float]]:
    if not HF_API_KEY:
        raise RuntimeError("HF_API_KEY is not set in the environment (.env)")

    headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            resp = httpx.post(
                HF_INFERENCE_URL,
                json={"inputs": texts},
                headers=headers,
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                vectors = data.get("embeddings", data) if isinstance(data, dict) else data
                if isinstance(vectors, list) and len(vectors) == len(texts):
                    return vectors
                raise ValueError(f"Unexpected HF response shape: {type(data)}")
            last_error = RuntimeError(f"HF inference HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        logger.warning("HF inference attempt %d/%d failed: %s", attempt + 1, retries, last_error)
        time.sleep(2 * (attempt + 1))

    raise RuntimeError(f"Embedding service unavailable after {retries} attempts: {last_error}")


class Embedder:
    def __init__(self, batch_size: int = EMBED_BATCH_SIZE):
        self.batch_size = batch_size

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = [t[:4000] for t in texts[i : i + self.batch_size]]
            out.extend(embed_hf(batch))
        return out
