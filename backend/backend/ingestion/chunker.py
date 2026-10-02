import re
import tiktoken
from pydantic import BaseModel
from typing import Optional
from backend.ingestion.loader import EpisodeRaw

class ChunkRaw(BaseModel):
    episode_slug: str
    ordinal: int
    text: str
    token_count: int
    speaker: Optional[str]
    chunk_start_time: Optional[str]

def chunk_episode(episode: EpisodeRaw, max_tokens: int = 500, overlap_tokens: int = 50) -> list[ChunkRaw]:
    enc = tiktoken.get_encoding("cl100k_base")
    # simplified chunking
    chunks = []
    lines = episode.raw_text.split("\n")
    current_chunk_text = ""
    current_tokens = 0
    ordinal = 1
    speaker = "Unknown"
    time = "00:00:00"
    
    for line in lines:
        match = re.match(r'^\*\*(.+?)\*\* \((\d{2}:\d{2}:\d{2})\):', line)
        if match:
            speaker = match.group(1)
            time = match.group(2)
        
        line_tokens = len(enc.encode(line))
        if current_tokens + line_tokens > max_tokens and current_tokens > 0:
            chunks.append(ChunkRaw(
                episode_slug=episode.slug,
                ordinal=ordinal,
                text=current_chunk_text,
                token_count=current_tokens,
                speaker=speaker,
                chunk_start_time=time
            ))
            ordinal += 1
            current_chunk_text = ""
            current_tokens = 0
        current_chunk_text += line + "\n"
        current_tokens += line_tokens
    
    if current_chunk_text:
        chunks.append(ChunkRaw(
            episode_slug=episode.slug,
            ordinal=ordinal,
            text=current_chunk_text,
            token_count=current_tokens,
            speaker=speaker,
            chunk_start_time=time
        ))
        
    return chunks
