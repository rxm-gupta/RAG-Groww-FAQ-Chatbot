"""API routes. Error handling never exposes keys, stack traces, credentials,
internal prompts, or raw retrieved chunks."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request

from ..config import settings
from ..rag.retriever import RetrievalError, get_client, get_document, list_documents
from ..safety import messages as M
from ..safety.pii import scan_pii
from ..schemas.models import (
    ChatRequest,
    ChatResponse,
    DocumentOut,
    IngestRequest,
    SearchHit,
    SearchRequest,
    SearchResponse,
    SourceInfo,
)
from ..services.chat_service import ServiceError, handle_chat
from ..utils.ratelimit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "app": "Groww Mutual Fund FAQ Assistant",
        "model": settings.groq_model,
        "embedding": "all-MiniLM-L6-v2 (HF Inference API)",
    }


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.chat_rate_limit)
def chat(request: Request, req: ChatRequest):
    try:
        return handle_chat(req.question, req.session_id)
    except ServiceError as exc:
        raise HTTPException(status_code=503, detail=exc.public_message)
    except Exception:  # noqa: BLE001
        logger.exception("Unhandled chat error")
        raise HTTPException(status_code=500, detail=M.GEN_ERROR_MSG)


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    pii = scan_pii(req.query)
    if pii.detected:
        raise HTTPException(status_code=422, detail=M.PII_MSG)
    from ..rag.reranker import rerank
    from ..rag.retriever import retrieve
    from ..safety.intent import classify_intent

    intent_result = classify_intent(req.query, False)
    try:
        client = get_client()
        hits = retrieve(client, req.query, req.scheme or intent_result.scheme,
                        req.topic or intent_result.topic, top_k=req.top_k)
    except RetrievalError:
        raise HTTPException(status_code=503, detail=M.DB_ERROR_MSG)
    ranked = rerank(hits, req.scheme or intent_result.scheme,
                    req.topic or intent_result.topic, intent_result.intent,
                    req.query)
    out = []
    for h in ranked[: req.top_k]:
        meta = h.get("metadata") or {}
        out.append(
            SearchHit(
                chunk_id=str(h.get("id")),
                document_id=str(h.get("document_id")),
                text_preview=(h.get("chunk_text") or "")[:300],
                page_number=h.get("page_number"),
                section=h.get("section"),
                scheme=h.get("scheme"),
                topic=h.get("topic"),
                similarity=round(float(h.get("similarity") or 0), 4),
                rerank_score=float(h.get("rerank_score") or 0),
                source=SourceInfo(
                    title=meta.get("document_title"), url=meta.get("source_url"),
                    page=h.get("page_number"), source_id=meta.get("source_id"),
                ),
            )
        )
    return SearchResponse(hits=out, intent=intent_result.intent)


@router.get("/schemes")
def schemes():
    return {"schemes": M.SUPPORTED_SCHEMES}


@router.get("/topics")
def topics():
    from ..safety.intent import TOPIC_KEYWORDS

    return {"topics": sorted(TOPIC_KEYWORDS.keys())}


@router.get("/sources/{source_id}", response_model=DocumentOut)
def sources(source_id: str):
    try:
        client = get_client()
        doc = get_document(client, source_id)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=M.DB_ERROR_MSG)
    if not doc:
        raise HTTPException(status_code=404, detail="Source not found")
    doc["document_date"] = str(doc.get("document_date") or "") or None
    doc["effective_date"] = str(doc.get("effective_date") or "") or None
    return DocumentOut(**doc)


@router.post("/ingest")
def ingest(req: IngestRequest, x_ingest_token: str | None = Header(default=None)):
    if settings.ingest_token and x_ingest_token != settings.ingest_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        from ingestion.ingest import run_ingestion  # project-root module

        summary = run_ingestion(limit=req.limit, only_file=req.file_name)
        return {"status": "completed", **summary}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail="Ingestion failed")
