"""Supabase pgvector retrieval with escalating metadata filters."""
from __future__ import annotations

import logging

from ..config import settings
from .embeddings import embed_query

logger = logging.getLogger(__name__)


class RetrievalError(Exception):
    pass


# Topic-keyword expansion: appended to the embedded query so ANN recall
# surfaces chunks phrased in document language (e.g. "Stated Asset
# Allocation" tables, riskometer level definitions) that the raw question
# wording misses.
TOPIC_QUERY_EXPANSION: dict[str, str] = {
    "asset_allocation": "stated asset allocation pattern equity debt securities money market instruments percentage of net assets",
    "riskometer": "risk-o-meter six levels of risk low to moderate moderate high very high product labeling cycle",
    "aum": "average assets under management AUM AMFI monthly average crore folio count",
    "minimum_investment": "minimum application amount lump sum purchase minimum investment",
    "lock_in": "lock-in period statutory lock-in redemption of units",
    "expense_ratio": "total expense ratio TER direct plan regular plan recurring expenses",
    "exit_load": "entry load exit load load structure contingent deferred sales charge",
    "tax_capital_gains": "capital gains statement download tax P&L realised gains report",
    "folio_statement": "folio number consolidated account statement CAS download",
    "stamp_duty": "stamp duty applicable on purchase SIP installment transaction",
    "tax_80c": "section 80C income tax deduction ELSS tax saving limit",
    "sip": "systematic investment plan SIP installment cancel modify pause",
    "redemption": "redemption withdrawal payout settlement bank account",
}


def _expand_query(question: str, topic: str | None) -> str:
    if not topic:
        return question
    expansion = TOPIC_QUERY_EXPANSION.get(topic)
    if not expansion:
        return question
    low = question.lower()
    # skip expansion when the question already uses the document phrasing
    core_terms = [t for t in expansion.split() if len(t) > 4]
    if sum(1 for t in core_terms if t in low) >= 3:
        return question
    return f"{question} {expansion}"


def get_client():
    if not settings.supabase_url or not settings.supabase_key:
        raise RetrievalError("Database not configured")
    from supabase import create_client

    return create_client(settings.supabase_url, settings.supabase_key)


def _match(client, vector: list[float], scheme: str | None, topic: str | None, k: int) -> list[dict]:
    resp = client.rpc(
        "match_chunks",
        {
            "query_embedding": vector,
            "match_count": k,
            "filter_scheme": scheme,
            "filter_topic": topic,
            "min_similarity": 0.0,  # threshold applied after reranking
        },
    ).execute()
    return resp.data or []


def retrieve(
    client,
    question: str,
    scheme: str | None = None,
    topic: str | None = None,
    top_k: int | None = None,
) -> list[dict]:
    """Hybrid-logic retrieval: embed -> ANN search -> metadata-aware candidate merge.

    HNSW applies WHERE filters after the approximate scan, which can badly
    under-return rows for filtered queries. We therefore:
      1. run one UNFILTERED ANN query (wide net), and
      2. additionally a SCHEME-FILTERED query with heavy overfetch,
    then merge/dedupe; reranking applies topic/scheme/source weights.
    A query-scoped scheme is never silently replaced by other schemes at answer
    time; that is enforced in the chat service.
    """
    top_k = top_k or settings.top_k
    question = _expand_query(question, topic)
    try:
        vector = embed_query(question)
    except Exception as exc:  # noqa: BLE001
        logger.error("Embedding failed: %s", exc)
        raise RetrievalError("embedding_failed") from exc

    overfetch = max(top_k * 6, 36)
    try:
        global_hits = _match(client, vector, None, None, overfetch)
        merged: dict[str, dict] = {h["id"]: h for h in global_hits}
        if scheme:
            for h in _match(client, vector, scheme, None, overfetch):
                merged.setdefault(h["id"], h)
            # cheap pre-filter: drop clearly wrong-scheme chunks when a specific
            # scheme was asked about (keeps reranker focused)
            merged = {
                i: h
                for i, h in merged.items()
                if not (h.get("scheme") and h.get("scheme") != scheme)
            }
        return list(merged.values())
    except RetrievalError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Vector search failed: %s", exc)
        raise RetrievalError("database_unavailable") from exc


def get_document(client, source_id: str) -> dict | None:
    resp = client.table("documents").select("*").eq("source_id", source_id).limit(1).execute()
    rows = resp.data or []
    return rows[0] if rows else None


def list_documents(client) -> list[dict]:
    resp = (
        client.table("documents")
        .select("id,source_id,title,scheme,organization,document_type,document_date,effective_date,source_url,file_name")
        .order("scheme")
        .execute()
    )
    return resp.data or []
