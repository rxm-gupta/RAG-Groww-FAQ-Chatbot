"""Lightweight reranker.

Factors: semantic similarity, exact scheme match, topic match, document-type
relevance (question-aware), document freshness, and official-source priority
(question-aware: HDFC scheme docs > HDFC pages > SEBI > AMFI > Groww).
"""
from __future__ import annotations

from datetime import date

# question-aware source priority: intent -> preferred organizations/doc types
INTENT_SOURCE_PRIORITY: dict[str, dict[str, list[str]]] = {
    "FACTUAL_SCHEME": {"organizations": ["HDFC Mutual Fund"], "doc_types": ["SID", "KIM", "FACTSHEET", "TER_DATA", "NAV_DATA", "AUM_DATA", "LEAFLET"]},
    "HISTORICAL_PERFORMANCE": {"organizations": ["HDFC Mutual Fund"], "doc_types": ["FACTSHEET", "PRESENTATION", "SID"]},
    "FACTUAL_GROWW": {"organizations": ["Groww"], "doc_types": ["GROWW_HELP", "OTHER"]},
    "FACTUAL_REGULATORY": {"organizations": ["SEBI", "AMFI"], "doc_types": ["FAQ_DATASET", "REGULATORY_FAQ", "TER_DATA"]},
    "FACTUAL_OPERATIONAL": {"organizations": ["HDFC Mutual Fund", "AMFI"], "doc_types": ["SID", "FAQ_DATASET", "KIM"]},
    # generic/definitional questions: SEBI FAQ dataset is the best definition source
    "AMBIGUOUS": {"organizations": ["SEBI"], "doc_types": ["FAQ_DATASET"]},
}
DEFAULT_PRIORITY = {"organizations": [], "doc_types": []}

ORG_RANK = {  # generic fallback ordering
    "HDFC Mutual Fund": 0.9,
    "SEBI": 0.8,
    "AMFI": 0.7,
    "Groww": 0.6,
}

WEIGHTS = {
    "similarity": 0.55,
    "scheme": 0.18,
    "topic": 0.14,
    "source": 0.08,
    "freshness": 0.05,
}


def _freshness(document_date: str | None) -> float:
    if not document_date:
        return 0.4
    try:
        d = date.fromisoformat(str(document_date)[:10])
    except ValueError:
        return 0.4
    age_days = max((date.today() - d).days, 0)
    return max(1.0 - age_days / 1095.0, 0.0)  # decays over ~3 years


def _token_set(text: str) -> set[str]:
    return {t for t in text.lower().split() if len(t) > 2}


def _demote_near_duplicates(ranked: list[dict]) -> None:
    """Penalize later chunks that are near-copies of an already-ranked chunk
    from the SAME document (table-row floods: TER reports and riskometer
    disclosures emit hundreds of near-identical rows that crowd out the
    definitional/aggregate chunks). Score-based order is recomputed after
    demotion so a distinct chunk from the same document can rise."""
    kept: list[tuple[str, set[str]]] = []
    demoted: list[dict] = []
    for h in ranked:
        doc_id = str(h.get("document_id") or (h.get("metadata") or {}).get("source_id") or "")
        tokens = _token_set(h.get("chunk_text") or "")
        is_dup = False
        for kept_doc, kept_tokens in kept:
            if kept_doc != doc_id or not kept_tokens or not tokens:
                continue
            union = kept_tokens | tokens
            if union and len(kept_tokens & tokens) / len(union) > 0.55:
                is_dup = True
                break
        if is_dup:
            h["rerank_score"] = round(h["rerank_score"] * 0.88, 4)
            demoted.append(h)
        else:
            kept.append((doc_id, tokens))
    if demoted:
        ranked.sort(key=lambda x: x["rerank_score"], reverse=True)


def rerank(
    hits: list[dict],
    query_scheme: str | None,
    query_topic: str | None,
    intent: str | None,
) -> list[dict]:
    priority = INTENT_SOURCE_PRIORITY.get(intent or "", DEFAULT_PRIORITY)

    for h in hits:
        meta = h.get("metadata") or {}
        sim = float(h.get("similarity") or 0.0)
        chunk_scheme = h.get("scheme") or ""
        chunk_topic = h.get("topic") or ""

        scheme_score = 1.0 if query_scheme and chunk_scheme == query_scheme else (
            -0.5 if query_scheme and chunk_scheme and chunk_scheme != query_scheme else 0.3
        )
        topic_score = 1.0 if query_topic and chunk_topic == query_topic else 0.2

        org = h.get("organization") or meta.get("organization") or ""
        doc_type = h.get("document_type") or meta.get("document_type") or ""
        if org in priority["organizations"]:
            source_score = 1.0
        elif org in ORG_RANK:
            source_score = ORG_RANK[org]
        else:
            source_score = 0.4
        if doc_type in priority["doc_types"]:
            source_score += 0.25

        fresh = _freshness(h.get("document_date") or meta.get("document_date"))

        score = (
            WEIGHTS["similarity"] * sim
            + WEIGHTS["scheme"] * scheme_score
            + WEIGHTS["topic"] * topic_score
            + WEIGHTS["source"] * min(source_score, 1.25) / 1.25
            + WEIGHTS["freshness"] * fresh
        )
        h["rerank_score"] = round(score, 4)
        # stash display metadata for the citation builder
        h.setdefault("organization", org)
        h.setdefault("document_type", doc_type)

    ranked = sorted(hits, key=lambda x: x["rerank_score"], reverse=True)
    _demote_near_duplicates(ranked)
    return ranked
