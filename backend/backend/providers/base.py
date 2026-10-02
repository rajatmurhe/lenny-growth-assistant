from abc import ABC, abstractmethod
from typing import AsyncIterator, Literal, Optional
from pydantic import BaseModel

class ChatMessage(BaseModel):
    role: str
    content: str

class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[ChatMessage], max_tokens: int, temperature: float) -> str:
        pass
        
    @abstractmethod
    async def stream(self, messages: list[ChatMessage], max_tokens: int, temperature: float) -> AsyncIterator[str]:
        pass
        
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        pass
        
    @abstractmethod
    async def health_check(self) -> dict:
        pass
