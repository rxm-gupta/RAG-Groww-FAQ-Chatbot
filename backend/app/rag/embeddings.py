"""Query-side embedding via the Hugging Face Inference API (online only)."""
from __future__ import annotations

import logging
import time

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


def embed_query(text: str) -> list[float]:
    if not settings.hf_api_key:
        raise RuntimeError("HF_API_KEY is not configured")
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            resp = httpx.post(
                settings.hf_inference_url,
                json={"inputs": [text[:4000]]},
                headers={"Authorization": f"Bearer {settings.hf_api_key}"},
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                vectors = data.get("embeddings", data) if isinstance(data, dict) else data
                vec = vectors[0]
                if len(vec) != 384:
                    raise ValueError(f"Unexpected embedding dimension: {len(vec)}")
                return vec
            # Retry on 429 / 5xx; fail fast on 4xx client errors (except 429)
            if resp.status_code in (429, 502, 503, 504):
                last_error = RuntimeError(f"HF inference HTTP {resp.status_code}")
            else:
                raise RuntimeError(f"HF inference HTTP {resp.status_code}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if "HF inference HTTP 4" in str(exc) and "429" not in str(exc):
                raise
        if attempt < 2:
            sleep = 2 * (attempt + 1)
            # Respect Retry-After if present
            try:
                ra = int(resp.headers.get("Retry-After", "0"))  # type: ignore[union-attr]
                if ra:
                    sleep = max(sleep, ra)
            except Exception:
                pass
            logger.warning("HF embed attempt %d failed (%s), retrying in %ds", attempt + 1, last_error, sleep)
            time.sleep(sleep)
    raise RuntimeError(f"Embedding service unavailable: {last_error}")
