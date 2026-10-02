from typing import Literal
from backend.providers.base import LLMProvider
import re

ROUTES = Literal["answer_with_sources", "write_ship30_essay", "create_artifact"]

SHIP30_PATTERNS = [
    r'\bship\s*30\b', r'\bessay\b', r'\bwrite.*\b(article|piece|post)\b',
    r'\bdraft.*essay\b', r'\batomic\s+essay\b'
]

ARTIFACT_PATTERNS = [
    r'\bcreate.*artifact\b', r'\bgenerate.*document\b', r'\bexport\b',
    r'\bdownloadable\b', r'\bone.?pager\b', r'\bmemo\b'
]

async def route(message: str, provider: LLMProvider) -> ROUTES:
    message_lower = message.lower()
    for p in SHIP30_PATTERNS:
        if re.search(p, message_lower):
            return "write_ship30_essay"
    for p in ARTIFACT_PATTERNS:
        if re.search(p, message_lower):
            return "create_artifact"
    return "answer_with_sources"
