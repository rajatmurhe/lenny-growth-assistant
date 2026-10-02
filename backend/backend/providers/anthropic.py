from backend.providers.base import LLMProvider, ChatMessage
from typing import AsyncIterator
from backend.config import settings

class AnthropicProvider(LLMProvider):
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.chat_model = settings.ANTHROPIC_CHAT_MODEL

    async def complete(self, messages: list[ChatMessage], max_tokens: int, temperature: float) -> str:
        response = await self.client.messages.create(
            model=self.chat_model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": m.role, "content": m.content} for m in messages]
        )
        return response.content[0].text

    async def stream(self, messages: list[ChatMessage], max_tokens: int, temperature: float) -> AsyncIterator[str]:
        async with self.client.messages.stream(
            model=self.chat_model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": m.role, "content": m.content} for m in messages]
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError("Anthropic embeddings not supported")

    async def health_check(self) -> dict:
        try:
            await self.complete([ChatMessage(role="user", content="hello")], 10, 0.0)
            return {"status": "ok", "model": self.chat_model, "latency_ms": 0}
        except Exception:
            return {"status": "down", "model": self.chat_model, "latency_ms": 0}
