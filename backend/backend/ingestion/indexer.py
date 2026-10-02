"""
Idempotent upsert of episodes and chunks to the database.
Uses content_hash to skip unchanged episodes.
Populates tsv (tsvector) for full-text search via SQL function.
"""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Chunk, Episode
from backend.ingestion.embedder import ChunkEmbedded
from backend.ingestion.loader import EpisodeRaw


async def upsert_episode_and_chunks(
    session: AsyncSession,
    episode: EpisodeRaw,
    chunks: list[ChunkEmbedded],
    embed_model: str,
) -> tuple[int, int]:
    """
    Idempotent upsert:
    - If episode exists with same content_hash → skip (return 0, 0)
    - If episode exists with different hash → delete old chunks, update episode, re-insert chunks
    - If new episode → insert episode and all chunks

    Returns: (episodes_upserted, chunks_created)
    """
    # Check existing episode
    result = await session.execute(
        select(Episode).where(Episode.slug == episode.slug)
    )
    existing = result.scalars().first()

    if existing and existing.content_hash == episode.content_hash:
        # No change — skip
        return 0, 0

    if existing:
        # Delete old chunks (cascaded but explicit for clarity)
        await session.execute(delete(Chunk).where(Chunk.episode_id == existing.id))
        # Update episode metadata
        existing.title = episode.title
        existing.guest = episode.guest
        existing.published_at = episode.published_at
        existing.source_path = episode.source_path
        existing.content_hash = episode.content_hash
        existing.post_url = episode.post_url
        existing.word_count = episode.word_count
        db_ep = existing
        await session.flush()
    else:
        # New episode
        db_ep = Episode(
            id=uuid.uuid4(),
            slug=episode.slug,
            title=episode.title,
            guest=episode.guest,
            published_at=episode.published_at,
            source_path=episode.source_path,
            content_hash=episode.content_hash,
            post_url=episode.post_url,
            word_count=episode.word_count,
        )
        session.add(db_ep)
        await session.flush()  # Get the ID assigned

    # Insert chunks with embeddings and tsv
    for chunk in chunks:
        chunk_id = uuid.uuid4()

        # Format embedding as PostgreSQL vector literal
        embedding_str = "[" + ",".join(str(v) for v in chunk.embedding) + "]"

        # Insert chunk via raw SQL to use vector type and compute tsv
        await session.execute(
            text("""
                INSERT INTO chunks (
                    id, episode_id, ordinal, text, token_count,
                    embedding, tsv, embed_model, speaker, chunk_start_time, created_at
                ) VALUES (
                    :id, :episode_id, :ordinal, :text, :token_count,
                    CAST(:embedding AS vector),
                    to_tsvector('english', :tsv_text),
                    :embed_model, :speaker, :chunk_start_time, NOW()
                )
            """),
            {
                "id": str(chunk_id),
                "episode_id": str(db_ep.id),
                "ordinal": chunk.ordinal,
                "text": chunk.text,
                "token_count": chunk.token_count,
                "embedding": embedding_str,
                "tsv_text": chunk.text[:100000],  # Postgres tsvector limit
                "embed_model": embed_model,
                "speaker": chunk.speaker,
                "chunk_start_time": chunk.chunk_start_time,
            },
        )

    await session.commit()
    return 1, len(chunks)
