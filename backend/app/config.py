"""Application configuration. Everything is environment-driven; nothing is hard-coded."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_fallback_model: str = "openai/gpt-oss-20b"
    groq_api_base: str = "https://api.groq.com/openai/v1"

    # Hugging Face embeddings (online only)
    hf_api_key: str = ""
    hf_inference_url: str = (
        "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
    )
    embed_batch_size: int = 32

    # Retrieval tuning (configurable thresholds — never hard-coded in business logic)
    min_similarity_score: float = 0.35
    top_k: int = 8
    final_top_k: int = 4

    # API behaviour
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    chat_rate_limit: str = "30/minute"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    ingest_token: str = ""  # if set, POST /ingest requires X-Ingest-Token header

    # Conversation memory
    session_ttl_seconds: int = 1800


settings = Settings()
