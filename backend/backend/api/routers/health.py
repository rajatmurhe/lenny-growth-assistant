"""Real health checks for database, Ollama, index."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_basic():
    return {"status": "ok"}


@router.get("/health/live")
async def health_live():
    """Liveness probe - just confirms the process is up."""
    return {"status": "alive"}




@router.get("/health/ready")
async def health_ready(db: AsyncSession = Depends(get_db)):
    checks = {}
    overall_status = "ready"

    # ── Database ─────────────────────────────────────────────────────────────
    t0 = time.monotonic()
    try:
        await db.execute(text("SELECT 1"))
        db_latency = int((time.monotonic() - t0) * 1000)
        checks["database"] = {"status": "ok", "latency_ms": db_latency}
    except Exception as e:
        checks["database"] = {"status": "down", "error": str(e), "latency_ms": -1}
        overall_status = "not_ready"

    # ── Ollama + chat model ───────────────────────────────────────────────────
    import httpx
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            tags_data = resp.json()
            model_names = [m["name"] for m in tags_data.get("models", [])]
            chat_model_present = any(
                settings.OLLAMA_CHAT_MODEL in name for name in model_names
            )
            embed_model_present = any(
                settings.OLLAMA_EMBED_MODEL in name for name in model_names
            )
            ollama_latency = int((time.monotonic() - t0) * 1000)
            checks["ollama"] = {
                "status": "ok",
                "model_present": chat_model_present,
                "model": settings.OLLAMA_CHAT_MODEL,
                "latency_ms": ollama_latency,
            }
            checks["embedding_model"] = {
                "status": "ok" if embed_model_present else "missing",
                "model": settings.OLLAMA_EMBED_MODEL,
            }
            if not chat_model_present:
                overall_status = "degraded"
    except Exception as e:
        checks["ollama"] = {
            "status": "down",
            "error": str(e),
            "model_present": False,
            "latency_ms": -1,
        }
        checks["embedding_model"] = {"status": "unknown"}
        if overall_status == "ready":
            overall_status = "degraded"

    # ── Index populated ───────────────────────────────────────────────────────
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM chunks"))
        chunk_count = result.scalar() or 0
        checks["index_populated"] = {
            "status": "ok" if chunk_count > 0 else "empty",
            "chunk_count": chunk_count,
        }
        if chunk_count == 0 and overall_status == "ready":
            overall_status = "degraded"
    except Exception:
        checks["index_populated"] = {"status": "unknown", "chunk_count": 0}

    # ── Anthropic ─────────────────────────────────────────────────────────────
    checks["anthropic"] = {
        "status": "configured" if settings.ANTHROPIC_API_KEY else "not_configured",
        "model": settings.ANTHROPIC_CHAT_MODEL,
    }

    return {"status": overall_status, "checks": checks}
