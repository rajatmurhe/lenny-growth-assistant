import asyncio
from backend.providers.base import LLMProvider
from backend.ingestion.chunker import ChunkRaw
from pydantic import BaseModel

class ChunkEmbedded(ChunkRaw):
    embedding: list[float]

async def embed_chunks(chunks: list[ChunkRaw], provider: LLMProvider, embed_model: str) -> list[ChunkEmbedded]:
    async def process(chunk):
        emb = await provider.embed(chunk.text)
        return ChunkEmbedded(**chunk.model_dump(), embedding=emb)
    
    return await asyncio.gather(*[process(c) for c in chunks])
