-- ============================================================
-- Groww Mutual Fund FAQ Assistant - Supabase / pgvector schema
-- Run in Supabase SQL editor (or psql) as migration 001.
-- ============================================================

create extension if not exists vector;

-- ------------------------------------------------------------
-- documents
-- ------------------------------------------------------------
create table if not exists documents (
    id             uuid primary key default gen_random_uuid(),
    source_id      text unique not null,
    title          text,
    scheme         text,
    organization   text,
    document_type  text,
    document_date  date,
    effective_date date,
    source_url     text,
    file_name      text,
    created_at     timestamptz not null default now()
);

create index if not exists idx_documents_scheme        on documents (scheme);
create index if not exists idx_documents_document_type on documents (document_type);
create index if not exists idx_documents_source_id     on documents (source_id);
create index if not exists idx_documents_organization  on documents (organization);

-- ------------------------------------------------------------
-- chunks
-- ------------------------------------------------------------
create table if not exists chunks (
    id          uuid primary key default gen_random_uuid(),
    document_id uuid references documents (id) on delete cascade,
    chunk_text  text not null,
    page_number integer,
    section     text,
    scheme      text,
    topic       text,
    embedding   vector(384),
    metadata    jsonb,
    created_at  timestamptz not null default now()
);

create index if not exists idx_chunks_scheme       on chunks (scheme);
create index if not exists idx_chunks_topic        on chunks (topic);
create index if not exists idx_chunks_document_id  on chunks (document_id);

-- HNSW index for cosine-similarity vector search
create index if not exists idx_chunks_embedding_hnsw
    on chunks using hnsw (embedding vector_cosine_ops);

-- ------------------------------------------------------------
-- feedback (no PII: sanitized/hashed question only)
-- ------------------------------------------------------------
create table if not exists feedback (
    id             uuid primary key default gen_random_uuid(),
    question_hash  text,
    question_snippet text,
    intent         text,
    retrieved_chunk_ids jsonb,
    source_id      text,
    helpful        boolean not null,
    created_at     timestamptz not null default now()
);

-- ------------------------------------------------------------
-- RPC: hybrid-filtered cosine similarity search
-- Called by the FastAPI backend via supabase-py .rpc(...)
-- similarity = 1 - cosine_distance, range [0, 1]
-- ------------------------------------------------------------
create or replace function match_chunks(
    query_embedding vector(384),
    match_count    int          default 8,
    filter_scheme  text         default null,
    filter_topic   text         default null,
    min_similarity float        default 0.0
)
returns table (
    id           uuid,
    document_id  uuid,
    chunk_text   text,
    page_number  integer,
    section      text,
    scheme       text,
    topic        text,
    metadata     jsonb,
    similarity   float
)
language sql stable
as $$
    select
        c.id,
        c.document_id,
        c.chunk_text,
        c.page_number,
        c.section,
        c.scheme,
        c.topic,
        c.metadata,
        1 - (c.embedding <=> query_embedding) as similarity
    from chunks c
    where (filter_scheme is null or c.scheme = filter_scheme)
      and (filter_topic  is null or c.topic  = filter_topic)
      and 1 - (c.embedding <=> query_embedding) >= min_similarity
    order by c.embedding <=> query_embedding
    limit match_count;
$$;
