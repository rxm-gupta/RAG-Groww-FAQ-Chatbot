# Groww Mutual Fund FAQ Assistant

A facts-only mutual-fund FAQ chatbot for retail users. It answers factual questions about five HDFC Mutual Fund schemes, mutual-fund operations, regulatory topics, and Groww's public mutual-fund processes using only retrieved evidence from official documents (SID, KIM, Fund Facts, SEBI, AMFI, and spreadsheets) stored in Supabase with pgvector.

It does not provide investment advice. Advice, performance predictions, fund comparisons/rankings, market-timing suggestions, and account/PII requests are detected and refused before retrieval.

---

## Supported Schemes

1. **HDFC FlexiCap Fund**
2. **HDFC Small Cap Fund**
3. **HDFC Large and Mid Cap Fund**
4. **HDFC Index Fund - Nifty 50 Plan**
5. **HDFC ELSS Tax Saver Fund**

---

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
Local embedding: fastembed (all-MiniLM-L6-v2, 384 dimensions, ONNX runtime)
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
- **Embeddings:** Local `fastembed` using `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, ONNX runtime) — runs under 150 MB RAM, completely preventing Render 512 MB free tier OOM crashes; no Hugging Face Inference API token required.
- **Generation:** Groq (`GROQ_MODEL`, default `openai/gpt-oss-120b` or configured model; configurable fallback)

---

## Safety Guarantees

| Rule | Implementation |
| :--- | :--- |
| **No investment advice** | `ADVICE` intent → polite refusal before retrieval |
| **No predictions / comparisons / market timing** | Dedicated refusal intent pipelines |
| **PII never leaves the app** | PAN, Aadhaar, folio, bank, OTP, phone, email, and credential scan runs first; blocked requests are never embedded, stored, or sent to Supabase/Groq |
| **No hallucinated citations** | LLM output is URL-stripped; the single citation comes strictly from chunk metadata |
| **No weak-evidence answers** | Configurable similarity threshold + wrong-scheme guard |
| **Ambiguous questions clarify** | *"Which HDFC Mutual Fund scheme would you like to know about?"* |
| **Historical performance** | Reported as fact only when present in a retrieved official source, never ranked or extrapolated |

---

## Project Structure

```text
frontend/                 Next.js chat UI (Vercel)
backend/app/
  main.py                 FastAPI entrypoint (lifespan, CORS, rate limiting, /ping)
  config.py               pydantic-settings, environment-driven config
  api/routes.py           /health, /chat, /search, /ingest, /sources/{id}, /schemes, /topics
  services/chat_service.py pipeline orchestration + conversation memory + citations
  rag/                    local fastembed embeddings, retriever, reranker, Groq generator
  safety/                 pii.py, intent.py, messages.py
ingestion/                extract → clean → chunk → embed (fastembed) → ingest
evaluation/               golden_questions.json, guardrail_tests.json, run_evaluation.py
scripts/                  bootstrap_manifest.py, fetch_groww_help.py, generate_eval.py, smoke_final.py
supabase/migrations/      001_init.sql, 002_exact_knn.sql
data/documents/           official documents copied here by the bootstrap script
data/manifest.csv         document metadata including official source URLs
```

---

## Setup

### Prerequisites
- Python 3.11+ and Node.js 18+
- A Supabase project with `pgvector` enabled
- A Groq API key
- Internet access on first startup so `fastembed` can download the local ONNX model weights
- No Hugging Face API token is required for embeddings

---

### 1. Clone and Configure Environment

```bash
git clone https://github.com/rxm-gupta/RAG-Groww-FAQ-Chatbot.git
cd RAG-Groww-FAQ-Chatbot

# Create virtual environment
python -m venv .venv

# Activate environment
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Create your local environment file
cp .env.example .env
```

Fill in the required values in `.env`:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GROQ_API_KEY`

Use the environment variable names and optional settings documented in `.env.example`. Never commit `.env` or API keys to GitHub.

---

### 2. Supabase Setup

1. Create a project at [Supabase](https://supabase.com).
2. Open **SQL Editor**, paste all of `supabase/migrations/001_init.sql`, and run it. This creates the required tables, vector column, indexes, and `match_chunks` retrieval RPC.
3. Paste all of `supabase/migrations/002_exact_knn.sql` into the SQL Editor and run it. This switches retrieval to exact KNN search for the small corpus.
4. Copy your Supabase project URL and database key into `.env`.

---

### 3. Document Ingestion

The knowledge base uses official documents stored in `HDFC MF PDFs/`. The bootstrap script copies the files into `data/documents/` and builds the manifest with scheme, document type, organization, and source URL metadata.

```bash
# Prepare documents
python scripts/bootstrap_manifest.py

# Ingest all documents
python -m ingestion.run

# Or ingest a single document
python -m ingestion.run --file "SID - HDFC Small Cap Fund dated November 21 2025_0.pdf"
```

- Chunks are section-aware rather than split using only fixed character counts.
- Long sections are split at sentence boundaries with overlap, and tables remain structured where supported.
- Every chunk carries metadata such as scheme, topic, page number, source URL, document title, and source ID.
- Re-ingestion is designed to be idempotent per source ID.
- Embeddings are generated locally using `fastembed` (`sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions). The exact same model is used during ingestion and query time, ensuring vectors remain 100% compatible.

---

### 4. Run Locally

**Start the backend (Terminal 1):**
```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

**Start the frontend (Terminal 2):**
```bash
cd frontend
npm install
npm run dev
```

- Frontend: `http://localhost:3000`
- Backend API Docs: `http://127.0.0.1:8000/docs`
- Backend Health Check: `http://127.0.0.1:8000/ping`

---

### 5. Evaluate

Optionally rebuild evaluation datasets from the FAQ workbook:
```bash
python scripts/generate_eval.py
```

Run the evaluation suite against the active local backend:
```bash
python evaluation/run_evaluation.py --base-url http://localhost:8000
```

The evaluation suite reports retrieval accuracy, citation accuracy, scheme identification, answer-length compliance, refusal accuracy, and PII blocking.

---

## Environment Variables

See `.env.example` for the complete configuration.

Core backend variables include:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GROQ_API_KEY`

Optional settings: `GROQ_MODEL`, `GROQ_FALLBACK_MODEL`, `MIN_SIMILARITY_SCORE`, `TOP_K`, `FINAL_TOP_K`, `CORS_ORIGINS`, `CHAT_RATE_LIMIT`, and `INGEST_TOKEN`.

**Similarity threshold:** The default `MIN_SIMILARITY_SCORE` is configurable. Tune it against the actual corpus and evaluation results; an overly high threshold can reject relevant evidence, while a low threshold can admit weak matches.

---

## Deployment

| Component | Platform | Configuration |
| :--- | :--- | :--- |
| **Frontend** | Vercel | Set project root to `frontend/`; configure `NEXT_PUBLIC_API_URL` to the public Render backend URL. |
| **Backend** | Render | Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --workers 1`<br>Build Command: `pip install -r requirements.txt`<br>Set environment variables in the Render dashboard. |
| **Database** | Supabase | Run SQL migrations once; ingest documents from your machine or use the authenticated ingestion endpoint. |

### Memory Optimization & Uptime on Render Free Tier
- **Low RAM Profile:** By using `fastembed` instead of PyTorch, memory consumption stays around **~120–150 MB**, running well inside Render's 512 MB ceiling.
- **Preventing Sleep:** Configure [UptimeRobot](https://uptimerobot.com) with an HTTP `GET` or `HEAD` check hitting `https://<your-render-app>.onrender.com/ping` every 5–10 minutes to prevent the 15-minute inactivity spin-down.
- **Build Cache:** When deploying changes that remove PyTorch/sentence-transformers, select **"Clear build cache & deploy"** in Render to wipe previous multi-gigabyte virtual environments.

---

## Privacy Rules

- Do not enter PAN, Aadhaar, OTPs, bank details, folio numbers, phone numbers, emails, or other personal/account information.
- PII detection runs before retrieval; blocked input is not passed to the local embedding model, Supabase, or Groq.
- Raw PII is never logged.
- Chat history is not persisted server-side beyond the in-memory scheme-context session.

---

## Known Limitations

- Answers depend on the quality and recency of the supplied documents. Re-ingest updated official documents periodically.
- Rule-based intent classification favors precision over recall; unusual phrasing may result in clarification instead of a refusal.
- The similarity threshold may need tuning after corpus changes.
- Ingestion operations should be run locally due to the resource footprint of PDF parsers.

---

## Disclaimer

**Facts-only assistant.** This chatbot provides factual information from official public sources and does not provide investment, financial, portfolio, or tax advice. Do not enter PAN, Aadhaar, OTPs, bank details, folio numbers, or other personal/account information.


![alt text](<Screenshot 2026-10-10 230755.png>)