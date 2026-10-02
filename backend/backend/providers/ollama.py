from backend.providers.base import LLMProvider, ChatMessage
import httpx
from typing import AsyncIterator
import json
from backend.config import settings

class OllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.chat_model = settings.OLLAMA_CHAT_MODEL
        self.embed_model = settings.OLLAMA_EMBED_MODEL
        self.timeout = settings.REQUEST_TIMEOUT_S

    async def complete(self, messages: list[ChatMessage], max_tokens: int, temperature: float) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.chat_model,
                        "messages": [{"role": m.role, "content": m.content} for m in messages],
                        "options": {"temperature": temperature, "num_predict": max_tokens},
                        "stream": False
                    }
                )
                response.raise_for_status()
                return response.json()["message"]["content"]
            except httpx.TimeoutException:
                raise Exception("Ollama complete request timed out")

    async def stream(self, messages: list[ChatMessage], max_tokens: int, temperature: float) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat",
                    json={
                        "model": self.chat_model,
                        "messages": [{"role": m.role, "content": m.content} for m in messages],
                        "options": {"temperature": temperature, "num_predict": max_tokens},
                        "stream": True
                    }
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            yield data["message"]["content"]
            except httpx.TimeoutException:
                raise Exception("Ollama stream request timed out")

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.embed_model, "prompt": text}
            )
            response.raise_for_status()
            return response.json()["embedding"]

    async def health_check(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                return {"status": "ok", "model": self.chat_model, "latency_ms": 0}
            except Exception:
                return {"status": "down", "model": self.chat_model, "latency_ms": 0}
