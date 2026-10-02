from sqlalchemy.ext.asyncio import AsyncSession
from backend.providers.base import LLMProvider
from backend.config import Settings
from backend.ingestion.loader import load_corpus
from backend.ingestion.chunker import chunk_episode
from backend.ingestion.embedder import embed_chunks
from backend.ingestion.indexer import upsert_episode_and_chunks
from pydantic import BaseModel

class IngestionResult(BaseModel):
    episodes_processed: int
    chunks_created: int
    status: str
    error_message: str | None = None

async def run_ingestion(db: AsyncSession, provider: LLMProvider, config: Settings) -> IngestionResult:
    try:
        episodes = load_corpus(config.TRANSCRIPT_DIR)
        ep_count = 0
        ch_count = 0
        for ep in episodes:
            chunks = chunk_episode(ep)
            embedded = await embed_chunks(chunks, provider, config.OLLAMA_EMBED_MODEL)
            e, c = await upsert_episode_and_chunks(db, ep, embedded, config.OLLAMA_EMBED_MODEL)
            ep_count += e
            ch_count += c
        return IngestionResult(episodes_processed=ep_count, chunks_created=ch_count, status="completed")
    except Exception as e:
        return IngestionResult(episodes_processed=0, chunks_created=0, status="failed", error_message=str(e))
