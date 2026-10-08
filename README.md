# Groww Mutual Fund FAQ Assistant

A **facts-only** mutual-fund FAQ chatbot for retail users. It answers factual questions about five HDFC Mutual Fund schemes, mutual-fund operations, regulatory topics, and Groww's public mutual-fund processes using only retrieved evidence from official documents (SID, KIM, Fund Facts, SEBI, AMFI, and spreadsheets) stored in Supabase with pgvector.

> **It does not provide investment advice.** Advice, performance predictions, fund comparisons/rankings, market-timing suggestions, and account/PII requests are detected and refused before retrieval.

---

## Supported schemes

1. HDFC FlexiCap Fund
2. HDFC Small Cap Fund
3. HDFC Large and Mid Cap Fund
4. HDFC Index Fund - Nifty 50 Plan
5. HDFC ELSS Tax Saver Fund

## Architecture

```text
User question
   ↓
[FastAPI] PII detection
   ← BEFORE external calls; raw PII is never logged or stored
   ↓
Intent classification (12 intents, rule-based)
   ↓
Scheme extraction (+ conversation memory for follow-ups)
   ↓
Topic extraction + query normalization
   ↓
Local embedding: all-MiniLM-L6-v2 (384 dimensions)
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

- **Frontend:** Next.js 14 + TypeScript + Tailwind CSS → Vercel
- **Backend:** FastAPI (Python) → Render / Railway / Fly.io (`render.yaml` included)
- **Database:** Supabase PostgreSQL + pgvector
- **Embeddings:** Local `sentence-transformers/all-MiniLM-L6-v2` model (384 dimensions); no Hugging Face Inference API token is required
- **Generation:** Groq (`GROQ_MODEL`, default `openai/gpt-oss-120b`; configurable fallback)

### Safety guarantees

| Rule | Implementation |
|---|---|
| No investment advice | `ADVICE` intent → polite refusal before retrieval |
| No predictions/comparisons/market timing | Dedicated refusal intents |
| PII never leaves the app | PAN/Aadhaar/folio/bank/OTP/phone/email/credential scan runs first; blocked requests are never embedded, stored, or sent to Supabase/Groq |
| No hallucinated citations | LLM output is URL-stripped; the single citation comes only from chunk metadata |
| No weak-evidence answers | Configurable similarity threshold + wrong-scheme guard |
| Ambiguous questions clarify | "Which HDFC Mutual Fund scheme would you like to know about?" |
| Historical performance | Reported as fact only when present in a retrieved official source, never ranked or extrapolated |

---

## Project structure

```text
frontend/                 Next.js chat UI (Vercel)
backend/app/
  main.py                 FastAPI entrypoint (CORS, rate limiting)
  config.py               pydantic-settings, environment-driven config
  api/routes.py           /health /chat /search /ingest /sources/{id} /schemes /topics
  services/chat_service.py pipeline orchestration + conversation memory + citations
  rag/                    local embeddings, retriever, reranker, Groq generator
  safety/                 pii.py, intent.py, messages.py
ingestion/                extract → clean → chunk → embed → ingest
evaluation/               golden_questions.json, guardrail_tests.json, run_evaluation.py
scripts/                  bootstrap_manifest.py, fetch_groww_help.py,
                          generate_eval.py, smoke_final.py
supabase/migrations/      001_init.sql, 002_exact_knn.sql
data/documents/           official documents copied here by the bootstrap script
data/manifest.csv         document metadata including official source URLs
```

---

## Setup

### Prerequisites

- Python 3.11+ and Node.js 18+
- A [Supabase](https://supabase.com/) project with pgvector enabled
- A [Groq](https://console.groq.com/) API key
- Internet access on first model load so `sentence-transformers` can download the public model
- No Hugging Face API token is required for embeddings

### 1. Clone and configure the environment

```bash
git clone https://github.com/rxm-gupta/RAG-Groww-FAQ-Chatbot.git
cd RAG-Groww-FAQ-Chatbot

python -m venv .venv

# Windows
.venv\Scripts\python -m pip install -r requirements.txt

# macOS/Linux
# .venv/bin/python -m pip install -r requirements.txt

# Create your local environment file
cp .env.example .env
```

Fill in the required values in `.env`, including:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GROQ_API_KEY`

Use the environment variable names and optional settings documented in `.env.example`. Never commit `.env` or API keys to GitHub.

### 2. Supabase setup

1. Create a project at [Supabase](https://supabase.com/).
2. Open **SQL Editor**, paste all of `supabase/migrations/001_init.sql`, and run it. This creates the required tables, vector column, indexes, and `match_chunks` retrieval RPC.
3. Paste all of `supabase/migrations/002_exact_knn.sql` into the SQL Editor and run it. This switches retrieval to exact KNN search for the small corpus.
4. Copy your Supabase project URL and appropriate database API key into `.env`, according to your backend configuration.

### 3. Document ingestion

The knowledge base uses official documents stored in `HDFC MF PDFs/`. The bootstrap script copies the files into `data/documents/` and builds the manifest with scheme, document type, organization, and source URL metadata.

```bash
python scripts/bootstrap_manifest.py
```

Then ingest the documents:

```bash
# Ingest all documents
python -m ingestion.run

# Ingest one document
python -m ingestion.run --file "SID - HDFC Small Cap Fund dated November 21 2025_0.pdf"
```

- Chunks are section-aware rather than split using only fixed character counts.
- Long sections are split at sentence boundaries with overlap, and tables remain structured where supported.
- Every chunk carries metadata such as scheme, topic, page number, source URL, document title, and source ID.
- Re-ingestion is designed to be idempotent per source ID.
- Embeddings are generated locally with `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions). The same model should be used for both ingestion and query-time embeddings so the vectors remain compatible.

**Important:** If you change the embedding model, its configuration, or the vector dimension, assess compatibility with the existing Supabase vectors before re-ingesting.

### 4. Run locally

Start the backend in Terminal 1:

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

Start the frontend in Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

Open the frontend at [http://localhost:3000](http://localhost:3000).

The backend API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 5. Evaluate

Optionally rebuild evaluation datasets from the FAQ workbook:

```bash
python scripts/generate_eval.py
```

Run the evaluation suite against the local backend:

```bash
python evaluation/run_evaluation.py --base-url http://localhost:8000
```

The evaluation suite reports retrieval accuracy, citation accuracy, scheme identification, answer-length compliance, refusal accuracy, and PII blocking.

---

## Environment variables

See `.env.example` for the complete configuration.

Core backend variables include:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GROQ_API_KEY`

Other configuration may include `GROQ_MODEL`, `GROQ_FALLBACK_MODEL`, `MIN_SIMILARITY_SCORE`, `TOP_K`, `FINAL_TOP_K`, `CORS_ORIGINS`, `CHAT_RATE_LIMIT`, and `INGEST_TOKEN`.

The application does not require `HF_API_KEY` or `HF_INFERENCE_URL` for embeddings when using the local model implementation.

> **Similarity threshold:** The default `MIN_SIMILARITY_SCORE` is configurable. Tune it against the actual corpus and evaluation results; an overly high threshold can reject relevant evidence, while a low threshold can admit weak matches.

---

## Deployment

| Component | Platform | Configuration |
|---|---|---|
| Frontend | **Vercel** | Set the project root to `frontend/` and configure `NEXT_PUBLIC_API_URL` to the public Render backend URL |
| Backend | **Render** | Install dependencies with `pip install -r requirements.txt`; start with `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`; configure the required environment variables and allowed CORS origin |
| Database | **Supabase** | Run the SQL migrations once; ingest documents from your machine or use the authenticated ingestion endpoint if configured |

### Embedding model at deployment

The backend runs `all-MiniLM-L6-v2` locally through `sentence-transformers`. The model may need to download on first startup, so the first startup can take longer. Hugging Face may serve as the public model download source, but the application does not call the Hugging Face Inference API for embedding requests.

Keep secrets in the Render and Vercel environment-variable dashboards. Never commit credentials to GitHub.

---

## Privacy rules

- Do not enter PAN, Aadhaar, OTPs, bank details, folio numbers, phone numbers, emails, or other personal/account information.
- PII detection runs before retrieval; blocked input is not passed to the local embedding model, Supabase, or Groq.
- Raw PII should never be logged.
- Chat history is not persisted server-side beyond the in-memory scheme-context session described by the application.

---

## Known limitations

- Answers depend on the quality and recency of the supplied documents. Re-ingest updated official documents periodically.
- Rule-based intent classification favors precision over recall; unusual phrasing may result in clarification instead of a refusal.
- The similarity threshold may need tuning after corpus changes.
- The first backend startup may take longer while the local embedding model downloads or loads.
- Groww-specific answers rely on ingested Groww help pages. If the relevant evidence is absent, the assistant should say the information was not found rather than guess.
- Deployment performance depends on the available CPU and memory resources.

---

## Disclaimer

**Facts-only assistant.** This chatbot provides factual information from official public sources and does not provide investment, financial, portfolio, or tax advice. Do not enter PAN, Aadhaar, OTPs, bank details, folio numbers, or other personal/account information.
