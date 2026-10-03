"""
Sessions router: CRUD + SSE message streaming with full agent pipeline.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import Artifact, Message, RetrievalEvent, Session
from backend.db.session import get_db
from backend.providers.factory import get_embed_provider, get_provider
from backend.retrieval.hybrid import hybrid_retrieve

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ── Pydantic schemas ────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    title: str | None = None
    provider: str = "ollama"


class MessageRequest(BaseModel):
    content: str


class ProviderUpdate(BaseModel):
    provider: str


# ── Helpers ─────────────────────────────────────────────────────────────────

def _session_to_dict(s: Session) -> dict:
    return {
        "id": str(s.id),
        "title": s.title,
        "provider": s.provider,
        "model": s.model,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _message_to_dict(m: Message) -> dict:
    return {
        "id": str(m.id),
        "session_id": str(m.session_id),
        "role": m.role,
        "content": m.content,
        "citations": m.citations,
        "skill_used": m.skill_used,
        "latency_ms": m.latency_ms,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


async def _sse_event(event_type: str, data: dict) -> str:
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload)}\n\n"


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("")
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    active_provider = body.provider or settings.ACTIVE_PROVIDER
    model = (
        settings.OLLAMA_CHAT_MODEL
        if active_provider == "ollama"
        else settings.ANTHROPIC_CHAT_MODEL
    )
    session = Session(
        id=uuid.uuid4(),
        title=body.title,
        provider=active_provider,
        model=model,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _session_to_dict(session)


@router.get("")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Session).order_by(Session.updated_at.desc()).limit(50)
    )
    sessions = result.scalars().all()
    return [_session_to_dict(s) for s in sessions]


@router.get("/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    data = _session_to_dict(session)
    data["messages"] = [_message_to_dict(m) for m in messages]
    return data


@router.post("/{session_id}/provider")
async def update_provider(
    session_id: str, body: ProviderUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if body.provider not in ("ollama", "anthropic"):
        raise HTTPException(status_code=400, detail="Provider must be 'ollama' or 'anthropic'")

    model = (
        settings.OLLAMA_CHAT_MODEL
        if body.provider == "ollama"
        else settings.ANTHROPIC_CHAT_MODEL
    )
    session.provider = body.provider
    session.model = model
    await db.commit()
    return {"provider": body.provider, "model": model}


@router.post("/{session_id}/messages")
async def post_message(
    session_id: str,
    request: Request,
    body: MessageRequest,
    db: AsyncSession = Depends(get_db),
):
    # Validate session
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    return StreamingResponse(
        _stream_response(session, body.content, db, request_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_response(
    session: Session,
    user_content: str,
    db: AsyncSession,
    request_id: str,
) -> AsyncIterator[str]:
    import structlog
    logger = structlog.get_logger()
    t_start = time.monotonic()

    # ── Save user message ────────────────────────────────────────────────────
    user_msg = Message(
        id=uuid.uuid4(),
        session_id=session.id,
        role="user",
        content=user_content,
    )
    db.add(user_msg)
    await db.commit()

    try:
        # ── Route request ────────────────────────────────────────────────────
        from backend.agents.router import route
        provider = get_provider(session.provider, settings)
        route_name = await route(user_content, provider)

        # ── Query rewrite (for follow-up condensation) ────────────────────────
        from backend.agents.rewriter import rewrite_query
        from backend.providers.base import ChatMessage

        # Load recent history (last 10 messages)
        msg_result = await db.execute(
            select(Message)
            .where(Message.session_id == session.id)
            .order_by(Message.created_at.asc())
            .limit(10)
        )
        history_msgs = msg_result.scalars().all()
        history = [
            ChatMessage(role=m.role, content=m.content)
            for m in history_msgs
            if m.id != user_msg.id
        ]

        t_retrieve_start = time.monotonic()
        standalone_query = await rewrite_query(user_content, history, provider)

        # ── Embed query ───────────────────────────────────────────────────────
        embed_provider = get_embed_provider(settings)
        query_embedding = await embed_provider.embed(standalone_query)

        # ── Hybrid retrieval ──────────────────────────────────────────────────
        chunks = await hybrid_retrieve(
            query=standalone_query,
            query_embedding=query_embedding,
            db=db,
            top_k=settings.RETRIEVAL_TOP_K,
            threshold=settings.RETRIEVAL_THRESHOLD,
        )
        t_retrieve_ms = int((time.monotonic() - t_retrieve_start) * 1000)

        # ── Insufficient evidence path ────────────────────────────────────────
        if not chunks:
            # Find closest episodes for guidance
            closest_sql = """
                SELECT DISTINCT e.title, e.guest
                FROM episodes e
                JOIN chunks c ON c.episode_id = e.id
                ORDER BY c.embedding <=> CAST(:emb AS vector)
                LIMIT 3
            """
            from sqlalchemy import text
            emb_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
            closest_result = await db.execute(text(closest_sql), {"emb": emb_str})
            closest = [
                f"{r.title}" + (f" (with {r.guest})" if r.guest else "")
                for r in closest_result.fetchall()
            ]

            insufficient_msg = (
                "I don't have sufficient evidence in the retrieved transcripts to answer this question confidently. "
                "This topic may not be covered in the available episodes, or may require more specific phrasing.\n\n"
                f"The most topically related episodes I found are:\n"
                + "\n".join(f"- {ep}" for ep in closest)
            )

            asst_msg = Message(
                id=uuid.uuid4(),
                session_id=session.id,
                role="assistant",
                content=insufficient_msg,
                skill_used="insufficient_evidence",
                latency_ms=int((time.monotonic() - t_start) * 1000),
            )
            db.add(asst_msg)
            await db.commit()

            yield await _sse_event("insufficient_evidence", {
                "message": insufficient_msg,
                "closest_episodes": closest,
            })
            yield await _sse_event("done", {})
            return

        # ── Route to skill ────────────────────────────────────────────────────
        if route_name == "write_ship30_essay":
            async for event in _handle_ship30(
                user_content, chunks, provider, session, db, t_start, history
            ):
                yield event
        elif route_name == "create_artifact":
            async for event in _handle_artifact(
                user_content, chunks, provider, session, db, t_start, history
            ):
                yield event
        else:
            # Default: answer_with_sources
            async for event in _handle_answer(
                user_content, standalone_query, chunks, provider, session, db,
                t_start, t_retrieve_ms, history, request_id
            ):
                yield event

    except Exception as e:
        logger.error("stream_error", error=str(e), request_id=request_id)
        yield await _sse_event("error", {"message": str(e), "code": "STREAM_ERROR"})
        yield await _sse_event("done", {})


async def _handle_answer(
    user_content: str,
    standalone_query: str,
    chunks,
    provider,
    session: Session,
    db: AsyncSession,
    t_start: float,
    t_retrieve_ms: int,
    history,
    request_id: str,
) -> AsyncIterator[str]:
    from backend.agents.answer import build_grounded_prompt
    from backend.agents.citation_validator import validate_citations
    from backend.providers.base import ChatMessage

    # Build grounded prompt
    system_msg, user_msg_content = build_grounded_prompt(user_content, chunks, history)

    messages = [
        ChatMessage(role="system", content=system_msg),
        ChatMessage(role="user", content=user_msg_content),
    ]

    # Stream tokens
    full_response = ""
    t_generate_start = time.monotonic()

    try:
        async for token in provider.stream(
            messages=messages,
            max_tokens=settings.MAX_TOKENS_GENERATE,
            temperature=0.1,
        ):
            full_response += token
            yield await _sse_event("token", {"content": token})
    except Exception as e:
        yield await _sse_event("error", {"message": str(e), "code": "GENERATION_ERROR"})
        yield await _sse_event("done", {})
        return

    t_generate_ms = int((time.monotonic() - t_generate_start) * 1000)

    # Validate citations
    chunk_ids = [c.chunk_id for c in chunks]
    validation = validate_citations(full_response, chunk_ids)

    # Build citation metadata for response
    citations = []
    for i, chunk in enumerate(chunks, start=1):
        if i <= len(chunks):
            citations.append({
                "ordinal": i,
                "chunk_id": chunk.chunk_id,
                "episode_slug": chunk.episode_slug,
                "episode_title": chunk.episode_title,
                "guest": chunk.guest,
                "post_url": chunk.post_url,
                "text_snippet": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                "rrf_score": chunk.rrf_score,
            })

    yield await _sse_event("citations", {"citations": citations, "validation": {
        "is_valid": validation.is_valid,
        "invalid_count": len(validation.invalid_citations),
    }})

    # Persist assistant message
    t_total_ms = int((time.monotonic() - t_start) * 1000)
    asst_msg = Message(
        id=uuid.uuid4(),
        session_id=session.id,
        role="assistant",
        content=full_response,
        citations=citations,
        skill_used="answer_with_sources",
        latency_ms=t_total_ms,
    )
    db.add(asst_msg)

    # Persist retrieval event
    retrieval_event = RetrievalEvent(
        id=uuid.uuid4(),
        message_id=asst_msg.id,
        query_used=standalone_query,
        chunk_ids=[c.chunk_id for c in chunks],
        scores=[c.rrf_score for c in chunks],
        retrieval_method="hybrid_rrf",
    )
    db.add(retrieval_event)

    # Update session title from first user message
    if not session.title:
        session.title = user_content[:80]
        db.add(session)

    await db.commit()

    yield await _sse_event("done", {"latency_ms": t_total_ms})


async def _handle_ship30(
    user_content: str,
    chunks,
    provider,
    session: Session,
    db: AsyncSession,
    t_start: float,
    history,
) -> AsyncIterator[str]:
    from backend.skills.ship30.pipeline import write_ship30_essay

    full_essay = ""
    async for event in write_ship30_essay(user_content, chunks, provider, settings):
        yield await _sse_event(event["type"], event)
        if event["type"] == "token":
            full_essay += event.get("content", "")

    t_total_ms = int((time.monotonic() - t_start) * 1000)

    asst_msg = Message(
        id=uuid.uuid4(),
        session_id=session.id,
        role="assistant",
        content=full_essay,
        skill_used="write_ship30_essay",
        latency_ms=t_total_ms,
    )
    db.add(asst_msg)
    if not session.title:
        session.title = user_content[:80]
        db.add(session)
    await db.commit()


async def _handle_artifact(
    user_content: str,
    chunks,
    provider,
    session: Session,
    db: AsyncSession,
    t_start: float,
    history,
) -> AsyncIterator[str]:
    from backend.agents.artifact_agent import create_artifact
    from backend.providers.base import ChatMessage

    h = [ChatMessage(role=m.role, content=m.content) for m in history]
    artifact_content = await create_artifact(
        request=user_content,
        conversation_context=h,
        retrieved_chunks=chunks,
        provider=provider,
        artifact_type="markdown",
    )

    t_total_ms = int((time.monotonic() - t_start) * 1000)

    artifact = Artifact(
        id=uuid.uuid4(),
        session_id=session.id,
        type="markdown",
        title=artifact_content.title,
        content=artifact_content.content,
        sanitized_content=artifact_content.sanitized_content,
        version=1,
    )
    db.add(artifact)

    asst_msg = Message(
        id=uuid.uuid4(),
        session_id=session.id,
        role="assistant",
        content=f"I've created an artifact: **{artifact_content.title}**",
        skill_used="create_artifact",
        latency_ms=t_total_ms,
    )
    asst_msg_id = asst_msg.id
    artifact.message_id = asst_msg_id
    db.add(asst_msg)

    if not session.title:
        session.title = user_content[:80]
        db.add(session)

    await db.commit()

    yield await _sse_event("artifact", {
        "artifact_id": str(artifact.id),
        "title": artifact_content.title,
        "type": "markdown",
    })
    yield await _sse_event("done", {"latency_ms": t_total_ms})
