"""Ingestion orchestrator: manifest -> extract -> clean -> chunk -> embed -> Supabase."""
from __future__ import annotations

import csv
import hashlib
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .config import DOCUMENTS_DIR, MANIFEST_PATH, SUPABASE_KEY, SUPABASE_URL
from .embed import Embedder

logger = logging.getLogger(__name__)

MANIFEST_FIELDS = [
    "file_name", "title", "scheme", "organization", "document_type",
    "document_date", "effective_date", "source_url", "source_id",
]


@dataclass
class ManifestRow:
    file_name: str
    title: str = ""
    scheme: str = ""
    organization: str = ""
    document_type: str = ""
    document_date: str = ""
    effective_date: str = ""
    source_url: str = ""
    source_id: str = ""


def load_manifest(path: Path | None = None) -> list[ManifestRow]:
    path = path or MANIFEST_PATH
    rows: list[ManifestRow] = []
    if not path.exists():
        logger.error("Manifest not found: %s (run scripts/bootstrap_manifest.py first)", path)
        return rows
    with open(path, newline="", encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            row = ManifestRow(**{k: (raw.get(k) or "").strip() for k in MANIFEST_FIELDS})
            if row.file_name:
                rows.append(row)
    return rows


def _make_source_id(row: ManifestRow) -> str:
    basis = row.source_id or f"{row.file_name}|{row.document_date}"
    return "src_" + hashlib.sha1(basis.encode()).hexdigest()[:12]


def _parse_date(value: str) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y", "%B %d, %Y", "%b %Y", "%B %Y"):
        try:
            from datetime import datetime

            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    import re

    m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", value)
    if m:
        try:
            from datetime import datetime

            d = datetime.strptime(f"{m.group(1)} 01 {m.group(2)}", "%B %d %Y").date()
            return d.isoformat()
        except ValueError:
            pass
    return None


def get_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in the environment (.env)")
    from supabase import create_client

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def ingest_row(client, embedder: Embedder, row: ManifestRow, documents_dir: Path | None = None) -> int:
    documents_dir = documents_dir or DOCUMENTS_DIR
    path = documents_dir / row.file_name
    if not path.exists():
        logger.warning("File missing on disk, skipping: %s", row.file_name)
        return 0

    # local imports keep module import light for tests
    from .chunk import chunk_document

    source_id = row.source_id or _make_source_id(row)

    # idempotency: remove previous version of this source
    existing = client.table("documents").select("id").eq("source_id", source_id).execute()
    for doc in existing.data or []:
        client.table("documents").delete().eq("id", doc["id"]).execute()

    chunks = chunk_document(path)
    if not chunks:
        logger.warning("No chunks produced for %s", row.file_name)
        return 0

    # Force correct topic for multi-scheme docs where every chunk is that topic
    # (header keyword only in first chunk, row chunks would otherwise be 'general')
    if "riskometer" in row.file_name.lower():
        for c in chunks:
            c.topic = "riskometer"
    if (row.document_type or "").upper() == "TER_DATA":
        # TER report rows mention Regular/Direct Plan more often than the
        # expense-ratio keywords, so keyword voting mislabels most chunks.
        for c in chunks:
            c.topic = "expense_ratio"

    vectors = embedder.embed([c.text for c in chunks])

    doc_payload = {
        "source_id": source_id,
        "title": row.title or row.file_name,
        "scheme": row.scheme or None,
        "organization": row.organization or None,
        "document_type": row.document_type or None,
        "document_date": _parse_date(row.document_date),
        "effective_date": _parse_date(row.effective_date),
        "source_url": row.source_url or None,
        "file_name": row.file_name,
    }
    ins = client.table("documents").insert(doc_payload).execute()
    document_id = ins.data[0]["id"]

    batch: list[dict] = []
    total = 0
    _nul = str.maketrans("", "", "\x00")

    def _safe(v) -> str:
        return v.translate(_nul) if isinstance(v, str) else v

    for c, vec in zip(chunks, vectors):
        # For multi-scheme docs (e.g., TER report) the manifest has no single scheme;
        # detect per-chunk so the wrong-scheme guard can match correctly.
        chunk_scheme = _safe(row.scheme) or None
        if not chunk_scheme:
            from .config import detect_scheme

            chunk_scheme = detect_scheme(c.text) or None

        batch.append(
            {
                "document_id": document_id,
                "chunk_text": _safe(c.text[:8000]),
                "page_number": c.page_number,
                "section": _safe(c.section[:200]),
                "scheme": chunk_scheme,
                "topic": c.topic,
                "embedding": vec,
                "metadata": {
                    "source_id": source_id,
                    "source_url": row.source_url or "",
                    "document_title": _safe(row.title or row.file_name),
                    "page_end": c.page_end,
                    "file_name": row.file_name,
                    "document_type": row.document_type,
                    "organization": row.organization,
                    "document_date": row.document_date,
                },
            }
        )
        if len(batch) >= 50:
            client.table("chunks").insert(batch).execute()
            total += len(batch)
            batch = []
    if batch:
        client.table("chunks").insert(batch).execute()
        total += len(batch)
    logger.info("Ingested %s: %d chunks (source_id=%s)", row.file_name, total, source_id)
    return total


def run_ingestion(limit: int | None = None, only_file: str | None = None) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    rows = load_manifest()
    if only_file:
        rows = [r for r in rows if r.file_name == only_file]
    if limit:
        rows = rows[:limit]
    client = get_client()
    embedder = Embedder()
    ok, failed, total_chunks = 0, 0, 0
    for row in rows:
        try:
            total_chunks += ingest_row(client, embedder, row)
            ok += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            logger.error("FAILED %s: %s", row.file_name, exc)
    summary = {"files_ok": ok, "files_failed": failed, "chunks_ingested": total_chunks}
    logger.info("Ingestion summary: %s", summary)
    return summary
