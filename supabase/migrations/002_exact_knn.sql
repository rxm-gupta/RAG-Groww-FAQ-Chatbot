-- ============================================================
-- Migration 002: make match_chunks use EXACT KNN.
--
-- Why: pgvector's HNSW index applies WHERE filters AFTER the
-- approximate nearest-neighbour scan. With metadata filters
-- (scheme/topic), the scan can stop early and return far fewer
-- rows than requested (observed: 15 of 396 matching chunks),
-- dropping the best evidence.
--
-- Our corpus is small (~2k chunks), so an exact sequential scan
-- is fast (<50 ms) and guarantees correct filtered ranking.
-- Revisit if the corpus grows beyond ~100k chunks.
-- ============================================================

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
language plpgsql volatile
as $$
begin
    -- force sequential scan -> exact distances, filters applied pre-rank
    -- (volatile is required: SET is not allowed in stable/immutable functions)
    execute 'SET LOCAL enable_indexscan = off';

    return query
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
    limit greatest(match_count, 1);
end;
$$;
