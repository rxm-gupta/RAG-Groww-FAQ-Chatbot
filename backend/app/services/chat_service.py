"""Chat orchestration: the full RAG + safety pipeline.

PII detection -> intent classification -> scheme extraction (with safe
conversation memory) -> query normalization -> embedding -> filtered vector
search -> reranking -> threshold gate -> generation -> app-controlled citation.
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field

from ..config import settings
from ..rag.generator import generate_answer_with_fallback, looks_like_no_evidence
from ..rag.reranker import rerank
from ..rag.retriever import RetrievalError, retrieve
from ..safety import messages as M
from ..safety.intent import SCHEME_ALIASES, IntentResult, classify_intent, extract_scheme
from ..safety.pii import scan_pii
from ..schemas.models import ChatResponse, SourceInfo

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    def __init__(self, public_message: str):
        self.public_message = public_message
        super().__init__(public_message)


# ---------------------------------------------------------------------------
# Conversation memory — safe fields only (scheme/topic context). Never PII.
# ---------------------------------------------------------------------------
@dataclass
class SessionContext:
    scheme: str | None = None
    topic: str | None = None
    updated_at: float = field(default_factory=time.time)


_sessions: dict[str, SessionContext] = {}


def _get_session(session_id: str | None) -> SessionContext:
    if not session_id:
        return SessionContext()
    now = time.time()
    sess = _sessions.get(session_id)
    if sess is None or now - sess.updated_at > settings.session_ttl_seconds:
        sess = SessionContext()
        _sessions[session_id] = sess
    # opportunistic cleanup
    stale = [k for k, v in _sessions.items() if now - v.updated_at > settings.session_ttl_seconds]
    for k in stale:
        _sessions.pop(k, None)
    return sess


def _remember(session_id: str | None, intent_result: IntentResult) -> None:
    if not session_id:
        return
    sess = _sessions.get(session_id)
    if sess is None:
        return
    if intent_result.scheme:
        sess.scheme = intent_result.scheme
    if intent_result.topic:
        sess.topic = intent_result.topic
    sess.updated_at = time.time()


# ---------------------------------------------------------------------------
# Citation builder — the ONLY place source URLs enter a response
# ---------------------------------------------------------------------------
def _format_last_updated(meta: dict) -> str:
    doc_date = meta.get("document_date") or ""
    date_str = str(doc_date)[:10]
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    try:
        year, month, _ = date_str.split("-")
        return f"{months[int(month) - 1]} {year}"
    except Exception:  # noqa: BLE001
        return date_str or "recently updated"


def build_citation(hit: dict) -> tuple[SourceInfo, str]:
    meta = hit.get("metadata") or {}
    source = SourceInfo(
        title=meta.get("document_title") or hit.get("section"),
        url=meta.get("source_url"),
        page=hit.get("page_number"),
        source_id=meta.get("source_id"),
    )
    return source, f"Last updated from sources: {_format_last_updated(meta)}"


def _question_hash(question: str) -> str:
    return hashlib.sha256(question.strip().lower().encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# AMBIGUOUS follow-up suggestions — try-answer-first appends these to answers
# ---------------------------------------------------------------------------
SCHEME_SUGGESTION_TEMPLATES: dict[str, str] = {
    "expense_ratio": "What is the expense ratio of {scheme}?",
    "exit_load": "Do you want to know about the exit load of {scheme}?",
    "benchmark": "What is the benchmark of {scheme}?",
    "minimum_investment": "What is the minimum investment for {scheme}?",
    "fund_manager": "Who is the fund manager of {scheme}?",
    "tracking_error": "What is the tracking error of {scheme}?",
    "asset_allocation": "What is the asset allocation of {scheme}?",
    "investment_objective": "What is the investment objective of {scheme}?",
    "investment_strategy": "What is the investment strategy of {scheme}?",
    "lock_in": "What is the lock-in period of {scheme}?",
    "plans_options": "What plans and options does {scheme} offer?",
    "replication": "Does {scheme} use full replication?",
    "riskometer": "What is the riskometer level of {scheme}?",
}

SUGGESTION_SCHEME_COUNT = 3


def build_scheme_suggestions(topic: str | None) -> str:
    template = SCHEME_SUGGESTION_TEMPLATES.get(topic, "Tell me about {scheme}")
    schemes = list(SCHEME_ALIASES.keys())[:SUGGESTION_SCHEME_COUNT]
    lines = "\n".join(f"- {template.format(scheme=s)}" for s in schemes)
    return f"You could also ask about a specific scheme:\n{lines}"


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def handle_chat(question_raw: str, session_id: str | None) -> ChatResponse:
    question = question_raw.strip()

    # 0. normalize whitespace
    question_norm = " ".join(question.split())

    # 1. PII detection — BEFORE retrieval/embedding/LLM. Never logged raw.
    pii = scan_pii(question_norm)
    logger.info("chat q_hash=%s pii=%s", _question_hash(question_norm), pii.safe_summary)

    # 2/3/4. intent + scheme + topic
    intent_result = classify_intent(question_norm, pii)

    # conversation-memory carry-over for follow-ups ("What about the exit load?")
    # Only for scheme-specific intents: operational how-tos ("how do I download
    # a capital-gains statement?") are scheme-agnostic processes, and injecting
    # a remembered scheme there pollutes retrieval and triggers the
    # wrong-scheme guard against neutral sources (blogs, SEBI/AMFI docs).
    sess = _get_session(session_id)
    if intent_result.intent in ("FACTUAL_SCHEME", "AMBIGUOUS") and not intent_result.scheme:
        if sess.scheme:
            intent_result.scheme = sess.scheme

    refused_type: str | None = None
    refusal_msg: str | None = None

    if pii.hard_identifier:
        refused_type, refusal_msg = "PII_ACCOUNT", M.PII_MSG
    elif intent_result.intent == "ADVICE":
        refused_type, refusal_msg = "ADVICE", M.ADVICE_MSG
    elif intent_result.intent == "PERFORMANCE_PREDICTION":
        refused_type, refusal_msg = "PERFORMANCE_PREDICTION", M.PREDICTION_MSG
    elif intent_result.intent == "PERFORMANCE_COMPARISON":
        refused_type, refusal_msg = "PERFORMANCE_COMPARISON", M.COMPARISON_MSG
    elif intent_result.intent == "MARKET_TIMING":
        refused_type, refusal_msg = "MARKET_TIMING", M.MARKET_TIMING_MSG
    elif intent_result.intent == "OUT_OF_SCOPE":
        refused_type, refusal_msg = "OUT_OF_SCOPE", M.OUT_OF_SCOPE_MSG
    elif intent_result.intent == "PII_ACCOUNT":
        refused_type, refusal_msg = "PII_ACCOUNT", M.PII_MSG

    if refusal_msg:
        _remember(session_id, intent_result)
        return ChatResponse(
            answer=refusal_msg,
            intent=intent_result.intent,
            scheme=intent_result.scheme,
            topic=intent_result.topic,
            source=None,
            last_updated=None,
            refused=True,
            refusal_type=refused_type,
        )

    # 5. query normalization: append resolved scheme context for embedding quality
    retrieval_query = question_norm
    if intent_result.scheme and intent_result.scheme.lower() not in question_norm.lower():
        retrieval_query = f"{question_norm} {intent_result.scheme}"

    # 6-8. embed + search + rerank
    from ..rag.retriever import get_client  # lazy import keeps unit tests DB-free

    try:
        client = get_client()
    except RetrievalError:
        raise ServiceError(M.DB_ERROR_MSG)

    try:
        hits = retrieve(client, retrieval_query, intent_result.scheme, intent_result.topic)
    except RetrievalError as exc:
        if "database_unavailable" in str(exc):
            raise ServiceError(M.DB_ERROR_MSG)
        raise ServiceError(M.GEN_ERROR_MSG)

    ranked = rerank(hits, intent_result.scheme, intent_result.topic, intent_result.intent, question_norm)

    ambiguous_try = intent_result.intent == "AMBIGUOUS" and not intent_result.scheme
    ambiguous_not_found = f"{M.AMBIGUOUS_NOT_FOUND_MSG}\n\n{build_scheme_suggestions(intent_result.topic)}"

    # 9. threshold gate (configurable MIN_SIMILARITY_SCORE)
    top = ranked[0] if ranked else None
    if not top or float(top.get("similarity") or 0) < settings.min_similarity_score:
        if ambiguous_try:
            return ChatResponse(
                answer=ambiguous_not_found,
                intent=intent_result.intent,
                scheme=intent_result.scheme,
                topic=intent_result.topic,
                source=None,
                last_updated=None,
                refused=False,
                refusal_type="NO_EVIDENCE",
            )
        return ChatResponse(
            answer=M.NOT_FOUND_MSG,
            intent=intent_result.intent,
            scheme=intent_result.scheme,
            topic=intent_result.topic,
            source=None,
            last_updated=None,
            refused=False,
            refusal_type="NO_EVIDENCE",
        )

    # wrong-scheme guard: if the user asked about a specific scheme, evidence
    # must match it OR be scheme-neutral (scheme=None: blogs, SEBI/AMFI docs,
    # process guides). Neutral sources can never leak another scheme's data,
    # so they complement matching evidence instead of being discarded.
    if intent_result.scheme:
        top_slice = ranked[: settings.final_top_k]
        matching = [h for h in top_slice if (h.get("scheme") or "") == intent_result.scheme]
        neutral = [h for h in top_slice if not (h.get("scheme") or "")]
        if not matching and not neutral:
            return ChatResponse(
                answer=M.NOT_FOUND_MSG,
                intent=intent_result.intent,
                scheme=intent_result.scheme,
                topic=intent_result.topic,
                source=None,
                last_updated=None,
                refused=False,
                refusal_type="SCHEME_MISMATCH",
            )
        evidence = matching + neutral
    else:
        evidence = ranked[: settings.final_top_k]

    # 10. generation (context passed separately; LLM never produces citations)
    try:
        answer_text, _model_used = generate_answer_with_fallback(evidence, question_norm)
    except RuntimeError:
        logger.error("Generation failed q_hash=%s", _question_hash(question_norm))
        raise ServiceError(M.GEN_ERROR_MSG)

    no_evidence = looks_like_no_evidence(answer_text)
    if no_evidence and ambiguous_try:
        return ChatResponse(
            answer=ambiguous_not_found,
            intent=intent_result.intent,
            scheme=intent_result.scheme,
            topic=intent_result.topic,
            source=None,
            last_updated=None,
            refused=False,
            refusal_type="NO_EVIDENCE",
        )

    if no_evidence:
        answer_text = M.NOT_FOUND_MSG

    if ambiguous_try:
        answer_text = f"{answer_text}\n\n{build_scheme_suggestions(intent_result.topic)}"

    # 11. citation from top chunk metadata only
    source, last_updated = build_citation(evidence[0])

    _remember(session_id, intent_result)

    return ChatResponse(
        answer=answer_text,
        intent=intent_result.intent,
        scheme=intent_result.scheme,
        topic=intent_result.topic,
        source=source,
        last_updated=last_updated,
        refused=False,
        refusal_type=None,
    )
