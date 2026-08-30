"""Pydantic request/response schemas."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Intent = Literal[
    "FACTUAL_SCHEME",
    "FACTUAL_OPERATIONAL",
    "FACTUAL_REGULATORY",
    "FACTUAL_GROWW",
    "HISTORICAL_PERFORMANCE",
    "ADVICE",
    "PERFORMANCE_PREDICTION",
    "PERFORMANCE_COMPARISON",
    "MARKET_TIMING",
    "PII_ACCOUNT",
    "OUT_OF_SCOPE",
    "AMBIGUOUS",
]


class SourceInfo(BaseModel):
    title: str | None = None
    url: str | None = None
    page: int | None = None
    source_id: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    session_id: str | None = Field(default=None, max_length=64)


class ChatResponse(BaseModel):
    answer: str
    intent: Intent
    scheme: str | None = None
    topic: str | None = None
    source: SourceInfo | None = None
    last_updated: str | None = None
    refused: bool
    refusal_type: str | None = None


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    text_preview: str
    page_number: int | None
    section: str | None
    scheme: str | None
    topic: str | None
    similarity: float
    rerank_score: float
    source: SourceInfo


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    scheme: str | None = Field(default=None, max_length=120)
    topic: str | None = Field(default=None, max_length=60)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    intent: Intent | None = None


class IngestRequest(BaseModel):
    file_name: str | None = Field(default=None, max_length=300)
    limit: int | None = Field(default=None, ge=1, le=200)


class DocumentOut(BaseModel):
    id: str
    source_id: str
    title: str | None
    scheme: str | None
    organization: str | None
    document_type: str | None
    document_date: str | None
    effective_date: str | None
    source_url: str | None
    file_name: str | None
