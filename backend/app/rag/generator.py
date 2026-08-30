"""Groq generation. The LLM sees only the retrieved context and returns ONLY
answer text — never URLs or citations (the application controls those)."""
from __future__ import annotations

import logging
import random
import re
import time

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the HDFC Mutual Fund FAQ Assistant.
You answer factual questions only.
Use ONLY the supplied retrieved context.
Never use unsupported world knowledge.
Never invent or infer missing facts.
Never fabricate URLs, citations, dates, figures, or scheme details.
If the supplied context does not contain enough evidence, say that the information could not be found in the official sources available to you.
Keep factual answers to a maximum of 3 sentences.
Do not provide investment advice.
Do not recommend, rank, compare, or select mutual funds for a user.
Do not predict future returns, NAV, or performance.
Historical performance may be reported only when explicitly present in an official retrieved source, without comparison, ranking, extrapolation, or recommendation.
Do not process account-specific information or PII.
If the question is an advice, prediction, market-timing, account-specific, or PII request, politely refuse and offer factual/educational information instead.
The application, not the model, controls the source URL.
Return only the factual answer text. Do not generate a source URL."""

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_NO_EVIDENCE_RE = re.compile(
    r"could(?:n'?t| not) (?:be )?(?:found|determined)|"
    r"not (?:available|contained|mentioned|provided|disclosed|specified|stated) in|"
    r"isn'?t available in|no (?:information|evidence|details)|"
    r"information you'?re looking for",
    re.IGNORECASE,
)

_CURLY_QUOTES = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
}


def _build_context(context_chunks: list[dict]) -> str:
    return "\n\n---\n\n".join(
        f"{(c.get('metadata') or {}).get('document_title') or ''} (page {c.get('page_number')})\n"
        f"{c.get('chunk_text', '')}"
        for c in context_chunks
    )


def _call_groq(model: str, context: str, question: str, timeout: float) -> str:
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 300,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"CONTEXT:\n{context}\n\nUSER QUESTION:\n{question}"},
        ],
    }
    for attempt in range(3):
        resp = httpx.post(
            f"{settings.groq_api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        if resp.status_code == 429 and attempt < 2:
            try:
                retry_after = float(resp.headers.get("Retry-After") or 0)
            except ValueError:
                retry_after = 0
            delay = min(max(retry_after, 1.0), 30.0) + random.uniform(0, 1.0)
            logger.warning("Groq 429 for %s, retrying in %.1fs", model, delay)
            time.sleep(delay)
            continue
        if resp.status_code != 200:
            raise RuntimeError(f"Groq HTTP {resp.status_code}")
        content = resp.json()["choices"][0]["message"]["content"]
        if not content or not content.strip():
            raise RuntimeError("Empty completion")
        return content.strip()
    raise RuntimeError(f"Groq HTTP 429 (retries exhausted) for {model}")


def looks_like_no_evidence(answer: str) -> bool:
    normalized = answer
    for curly, plain in _CURLY_QUOTES.items():
        normalized = normalized.replace(curly, plain)
    return bool(_NO_EVIDENCE_RE.search(normalized))


def generate_answer_with_fallback(context_chunks: list[dict], question: str) -> tuple[str, str]:
    """Try primary model then fallback. Returns (answer, model_used).
    Raises RuntimeError when both fail."""
    context = _build_context(context_chunks)
    errors: list[str] = []
    for model in dict.fromkeys([settings.groq_model, settings.groq_fallback_model]):
        if not model:
            continue
        try:
            raw = _call_groq(model, context, question, timeout=45)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{model}: {exc}")
            logger.warning("Generation failed (%s), trying next", exc)
            continue

        # strip any hallucinated URLs — citations are app-controlled
        answer = _URL_RE.sub("", raw).strip()
        answer = re.sub(r"\s{2,}", " ", answer).strip()
        if answer:
            return answer, model
        errors.append(f"{model}: empty answer")

    raise RuntimeError("; ".join(errors) or "no model configured")
