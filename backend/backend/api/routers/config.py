"""Config router: provider availability and model info."""
from __future__ import annotations

import httpx
from fastapi import APIRouter

from backend.config import settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/providers")
async def list_providers():
    """Return available LLM providers with their status."""
    providers = []

    # ── Ollama provider ──────────────────────────────────────────────────────
    ollama_available = False
    ollama_reason = None
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                tags = resp.json().get("models", [])
                model_names = [m["name"] for m in tags]
                chat_present = any(settings.OLLAMA_CHAT_MODEL in n for n in model_names)
                if chat_present:
                    ollama_available = True
                else:
                    ollama_reason = (
                        f"Model '{settings.OLLAMA_CHAT_MODEL}' not found in Ollama. "
                        f"Run: ollama pull {settings.OLLAMA_CHAT_MODEL}"
                    )
            else:
                ollama_reason = f"Ollama returned HTTP {resp.status_code}"
    except Exception as e:
        ollama_reason = f"Ollama unreachable at {settings.OLLAMA_BASE_URL}: {str(e)[:80]}"

    providers.append({
        "name": "ollama",
        "available": ollama_available,
        "reason": ollama_reason,
        "models": {
            "chat": settings.OLLAMA_CHAT_MODEL,
            "embed": settings.OLLAMA_EMBED_MODEL,
        },
    })

    # ── Anthropic provider ───────────────────────────────────────────────────
    anthropic_available = bool(settings.ANTHROPIC_API_KEY)
    anthropic_reason = None if anthropic_available else (
        "ANTHROPIC_API_KEY is not set. Add it to .env to enable cloud mode."
    )

    providers.append({
        "name": "anthropic",
        "available": anthropic_available,
        "reason": anthropic_reason,
        "models": {
            "chat": settings.ANTHROPIC_CHAT_MODEL,
        },
    })

    return {"providers": providers, "active": settings.ACTIVE_PROVIDER}
