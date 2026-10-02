"""
Hybrid retrieval: pgvector cosine similarity + Postgres full-text search,
merged with Reciprocal Rank Fusion (RRF).
"""
from __future__ import annotations

import json
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class RetrievedChunk(BaseModel):
    chunk_id: str
    episode_slug: str
    episode_title: str
    guest: Optional[str] = None
    post_url: Optional[str] = None
    text: str
    ordinal: int
    rrf_score: float
    vector_score: float
    fts_score: float


async def hybrid_retrieve(
    query: str,
    query_embedding: list[float],
    db: AsyncSession,
    top_k: int = 10,
    threshold: float = 0.35,
) -> list[RetrievedChunk]:
    """
    1. Vector search: cosine distance via pgvector <=> operator
    2. Full-text search: Postgres plainto_tsquery
    3. Merge with Reciprocal Rank Fusion (k=60)
    4. Normalize scores, filter by threshold, return top_k
    """
    candidate_k = top_k * 3  # over-fetch for RRF merging
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # ── 1. Vector search ───────────────────────────────────────────────────
    vector_sql = text("""
        SELECT
            c.id::text AS chunk_id,
            e.slug AS episode_slug,
            e.title AS episode_title,
            e.guest,
            e.post_url,
            c.text AS chunk_text,
            c.ordinal,
            1 - (c.embedding <=> CAST(:embedding AS vector)) AS vector_score
        FROM chunks c
        JOIN episodes e ON e.id = c.episode_id
        ORDER BY c.embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
    """)

    vector_result = await db.execute(
        vector_sql,
        {"embedding": embedding_str, "limit": candidate_k},
    )
    vector_rows = vector_result.fetchall()

    # ── 2. Full-text search ────────────────────────────────────────────────
    fts_sql = text("""
        SELECT
            c.id::text AS chunk_id,
            e.slug AS episode_slug,
            e.title AS episode_title,
            e.guest,
            e.post_url,
            c.text AS chunk_text,
            c.ordinal,
            ts_rank(c.tsv, plainto_tsquery('english', :query)) AS fts_score
        FROM chunks c
        JOIN episodes e ON e.id = c.episode_id
        WHERE c.tsv @@ plainto_tsquery('english', :query)
        ORDER BY fts_score DESC
        LIMIT :limit
    """)

    fts_result = await db.execute(fts_sql, {"query": query, "limit": candidate_k})
    fts_rows = fts_result.fetchall()

    # ── 3. Reciprocal Rank Fusion ──────────────────────────────────────────
    K = 60  # RRF constant

    # Build ranked lists
    vector_ranks: dict[str, int] = {}
    for rank, row in enumerate(vector_rows, start=1):
        vector_ranks[row.chunk_id] = rank

    fts_ranks: dict[str, int] = {}
    for rank, row in enumerate(fts_rows, start=1):
        fts_ranks[row.chunk_id] = rank

    # Collect all unique chunk IDs
    all_chunk_ids = set(vector_ranks.keys()) | set(fts_ranks.keys())

    # Build chunk metadata map
    chunk_meta: dict[str, dict] = {}
    for row in vector_rows:
        chunk_meta[row.chunk_id] = {
            "chunk_id": row.chunk_id,
            "episode_slug": row.episode_slug,
            "episode_title": row.episode_title,
            "guest": row.guest,
            "post_url": row.post_url,
            "text": row.chunk_text,
            "ordinal": row.ordinal,
            "vector_score": float(row.vector_score),
            "fts_score": 0.0,
        }
    for row in fts_rows:
        if row.chunk_id in chunk_meta:
            chunk_meta[row.chunk_id]["fts_score"] = float(row.fts_score)
        else:
            chunk_meta[row.chunk_id] = {
                "chunk_id": row.chunk_id,
                "episode_slug": row.episode_slug,
                "episode_title": row.episode_title,
                "guest": row.guest,
                "post_url": row.post_url,
                "text": row.chunk_text,
                "ordinal": row.ordinal,
                "vector_score": 0.0,
                "fts_score": float(row.fts_score),
            }

    # Calculate RRF scores
    scored: list[tuple[str, float]] = []
    for chunk_id in all_chunk_ids:
        v_rank = vector_ranks.get(chunk_id, candidate_k + K)
        f_rank = fts_ranks.get(chunk_id, candidate_k + K)
        rrf_score = (1.0 / (K + v_rank)) + (1.0 / (K + f_rank))
        scored.append((chunk_id, rrf_score))

    scored.sort(key=lambda x: x[1], reverse=True)

    # ── 4. Filter and return ───────────────────────────────────────────────
    results: list[RetrievedChunk] = []

    for chunk_id, raw_rrf in scored[:top_k * 2]:
        meta = chunk_meta[chunk_id]
        
        # Absolute thresholding based on vector score (cosine similarity).
        # Assuming vector_score is cosine distance (lower is closer).
        # If the best match is too far (e.g. distance > 0.65), it's irrelevant.
        if meta["vector_score"] > (1.0 - threshold):
            continue
            
        results.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                episode_slug=meta["episode_slug"],
                episode_title=meta["episode_title"],
                guest=meta["guest"],
                post_url=meta["post_url"],
                text=meta["text"],
                ordinal=meta["ordinal"],
                rrf_score=raw_rrf,
                vector_score=meta["vector_score"],
                fts_score=meta["fts_score"],
            )
        )

        if len(results) >= top_k:
            break

    return results
