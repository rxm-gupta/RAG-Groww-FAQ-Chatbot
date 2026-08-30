# Groww Mutual Fund FAQ Assistant

A **facts-only** mutual-fund FAQ chatbot for retail users. It answers factual questions about five HDFC Mutual Fund schemes, mutual-fund operations, regulatory topics, and Groww's public mutual-fund processes — using **only** retrieved evidence from official documents (SID / KIM / Fund Facts / SEBI / AMFI / spreadsheets) stored in Supabase with pgvector.

> **It does not provide investment advice.** Advice, performance predictions, fund comparisons/rankings, market-timing suggestions, and account/PII requests are detected and refused before retrieval.

---

## Supported schemes

1. HDFC FlexiCap Fund
2. HDFC Small Cap Fund
3. HDFC Large and Mid Cap Fund
4. HDFC Index Fund - Nifty 50 Plan
5. HDFC ELSS Tax Saver Fund

## Architecture

```
User question
   ↓
[FastAPI] PII detection            ← BEFORE any external call; raw PII never logged/stored
   ↓
Intent classification (12 intents, rule-based)
   ↓
Scheme extraction (+ conversation memory for follow-ups)
   ↓
Topic extraction + query normalization
   ↓
Embedding: all-MiniLM-L6-v2 via HF Inference API (online only)
   ↓
Supabase pgvector search (metadata-filtered RPC match_chunks)
   ↓
Reranking (similarity + scheme/topic match + question-aware source priority + freshness)
   ↓
Configurable threshold gate (MIN_SIMILARITY_SCORE)
   ↓
Groq generation (context passed separately; LLM returns answer text only)
   ↓
App-controlled citation (exactly ONE source link from chunk metadata)
   + "Last updated from sources"
```

- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS → Vercel
- **Backend**: FastAPI (Python) → Render / Railway / Fly.io (`render.yaml` included)
- **Database**: Supabase PostgreSQL + pgvector (HNSW index)
- **Embeddings**: Hugging Face Inference API — all-MiniLM-L6-v2 *online only*, no local models
- **Generation**: Groq (`GROQ_MODEL`, default `OpenAI GPT-OSS 120B`; configurable fallback)

### Safety guarantees

| Rule | Implementation |
|---|---|
| No investment advice | `ADVICE` intent → polite refusal before retrieval |
| No predictions/comparisons/market timing | Dedicated refusal intents |
| PII never leaves the app | PAN/Aadhaar/folio/bank/OTP/phone/email/credential regex scan runs **first**; blocked requests are never embedded, stored, or sent to Supabase/Groq |
| No hallucinated citations | LLM output is URL-stripped; the single citation comes only from chunk metadata |
| No weak-evidence answers | Configurable similarity threshold + wrong-scheme guard |
| Ambiguous questions clarify | "Which HDFC Mutual Fund scheme would you like to know about?" |
| Historical performance | Reported as fact **only** when present in a retrieved official source, never ranked/extrapolated |

---

## Project structure

```
frontend/                 Next.js chat UI (Vercel)
backend/app/
  main.py                 FastAPI entrypoint (CORS, rate limiting)
  config.py               pydantic-settings, all env-driven
  api/routes.py           /health /chat /search /ingest /sources/{id} /schemes /topics
  services/chat_service.py pipeline orchestration + conversation memory + citations
  rag/                    embeddings, retriever, reranker, Groq generator
  safety/                 pii.py, intent.py, messages.py (refusal wording lives here)
ingestion/                extract → clean → chunk → embed → ingest (one command)
evaluation/               golden_questions.json, guardrail_tests.json, run_evaluation.py
scripts/                  bootstrap_manifest.py, fetch_groww_help.py,
                          generate_eval.py, smoke_final.py
supabase/migrations/      001_init.sql (tables, HNSW index, match_chunks RPC),
                          002_exact_knn.sql (exact KNN match_chunks)
data/documents/           official documents (copied here by the bootstrap script)
data/manifest.csv         document metadata incl. official source URLs
```

---

## Setup

### Prerequisites
- Python 3.11+ and Node.js 18+
- A [Supabase](https://supabase.com) project (pgvector enabled)
- A [Groq](https://console.groq.com) API key
- A [Hugging Face](https://huggingface.co/settings/tokens) token with Inference API access

### 1. Clone & environment

```bash
git clone https://github.com/rxm-gupta/RAG-Groww-FAQ-Chatbot.git
cd RAG-Groww-FAQ-Chatbot
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt   # Windows
# .venv/bin/pip install -r requirements.txt       # macOS/Linux

cp .env.example .env    # then fill in SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY, HF_API_KEY
```

### 2. Supabase setup

1. Create a project at supabase.com.
2. SQL Editor → paste **all of `supabase/migrations/001_init.sql`** → Run.
   This creates `documents`, `chunks`, `feedback` (no longer used by the app), a `vector(384)` column with an **HNSW index**, btree indexes on scheme/topic/document_type/source_id, and the `match_chunks` RPC used by retrieval.
3. SQL Editor → paste **all of `supabase/migrations/002_exact_knn.sql`** → Run.
   This switches `match_chunks` to an exact KNN scan so metadata filters can't silently drop the best evidence (HNSW applies WHERE filters after the approximate scan). The corpus is small, so exact search is fast and correct.
4. Copy Project URL + **service-role key** into `.env`.

### 3. Document ingestion

The knowledge base ships in `HDFC MF PDFs/`. One-time bootstrap copies files into `data/documents/` and builds the manifest (scheme, doc type, organization, official source URLs pulled from the FAQ workbook):

```bash
python scripts/bootstrap_manifest.py
```

Then ingest everything (extract → clean → section-aware chunk → embed → upsert):

```bash
python -m ingestion.run              # all files
python -m ingestion.run --file "SID - HDFC Small Cap Fund dated November 21 2025_0.pdf"  # one file
```

- Chunks are **section-aware**, not blind fixed-size: headings delimit sections, long sections split at sentence boundaries with overlap, tables stay structured.
- Every chunk carries `{scheme, topic, page_number, source_url, document_title, source_id}` metadata.
- Re-ingesting is idempotent per `source_id`.
- Embeddings go exclusively through the HF Inference API (384-dim). If HF is down the run fails loudly — no local fallback model exists.

### 4. Run locally

```bash
# Terminal 1 — backend
uvicorn backend.app.main:app --port 8000

# Terminal 2 — frontend
cd frontend && npm install && npm run dev    # http://localhost:3000
```

### 5. Evaluate

```bash
python scripts/generate_eval.py          # rebuild datasets from the FAQ workbook (optional)
python evaluation/run_evaluation.py --base-url http://localhost:8000
```

Reports retrieval accuracy, citation accuracy, scheme identification, faithfulness length compliance, refusal accuracy, and PII blocking.

---

## Environment variables

See `.env.example`. Required: `SUPABASE_URL`, `SUPABASE_KEY`, `GROQ_API_KEY`, `HF_API_KEY`.
Key tunables: `GROQ_MODEL`, `GROQ_FALLBACK_MODEL`, `MIN_SIMILARITY_SCORE` (evidence gate), `TOP_K`, `FINAL_TOP_K`, `CORS_ORIGINS`, `CHAT_RATE_LIMIT`.

> **Note on MIN_SIMILARITY_SCORE:** the spec example suggests 0.70, but MiniLM cosine similarities for genuinely relevant chunks typically land between 0.30–0.60; a 0.70 gate rejects almost everything. The shipped default of **0.35** balances recall vs. safety and remains fully configurable.

## Deployment

| Piece | Platform | Notes |
|---|---|---|
| Frontend | **Vercel** | Root dir `frontend/`; env `NEXT_PUBLIC_API_URL=https://<render-app>.onrender.com` |
| Backend | **Render** | Use `render.yaml` blueprint or manual: build `pip install -r requirements.txt`, start `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`; set env vars; set `CORS_ORIGINS=https://<vercel-app>.vercel.app` |
| Database | **Supabase** | Run migration once; ingestion runs from your machine (or authenticated `POST /ingest` with `INGEST_TOKEN`) |

Secrets live only in platform dashboards — never in git.

## Privacy rules

- Do not enter PAN, Aadhaar, OTPs, bank details, folio numbers, phone numbers, or other personal/account information.
- PII is detected **before** retrieval; blocked input is never sent to the embedding API, Supabase, or Groq.
- Raw PII is never logged.
- Chat history is not persisted server-side beyond an in-memory scheme-context session (TTL 30 min).

## Known limitations

- Answers depend on the quality/recency of supplied documents; re-ingest updated factsheets periodically (`document_date` freshness feeds reranking).
- Rule-based intent classification favors precision over recall; unusual phrasings may route to clarification rather than refusal.
- The similarity threshold may need tuning after corpus changes.
- Grow-specific answers rely on ingested Groww pages; if absent, the assistant says the information wasn't found rather than guessing.

## Disclaimer

**Facts-only assistant.** This chatbot provides factual information from official public sources and does not provide investment, financial, portfolio, or tax advice. Do not enter PAN, Aadhaar, OTPs, bank details, folio numbers, or other personal/account information.
