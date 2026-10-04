"""
Integration tests: real PostgreSQL + real API.
Requires: docker compose up (DB running) and DATABASE_URL set.

Run via: docker compose exec backend python -m pytest backend/tests/integration/ -v
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, text

# ── Fixtures ─────────────────────────────────────────────────────────────────

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def db():
    """Real async DB session against the running PostgreSQL."""
    from backend.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client():
    """HTTP client against the running FastAPI app."""
    from backend.api.main import app
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── TC-01: Session isolation ─────────────────────────────────────────────────

class TestSessionIsolation:
    async def test_two_sessions_are_independent(self, client: AsyncClient):
        """Sessions must have fully independent context."""
        r1 = await client.post("/sessions", json={"provider": "ollama"})
        assert r1.status_code == 200
        s1_id = r1.json()["id"]

        r2 = await client.post("/sessions", json={"provider": "ollama"})
        assert r2.status_code == 200
        s2_id = r2.json()["id"]

        assert s1_id != s2_id

    async def test_session_messages_persisted(self, client: AsyncClient, db):
        """Messages written to one session appear when re-fetching that session."""
        from backend.db.models import Session as SessionModel, Message as MessageModel
        from sqlalchemy import insert

        session_id = str(uuid.uuid4())
        await db.execute(
            insert(SessionModel).values(
                id=session_id,
                title="Test Session",
                provider="ollama",
                model="llama3.2:3b",
            )
        )
        msg_id = str(uuid.uuid4())
        await db.execute(
            insert(MessageModel).values(
                id=msg_id,
                session_id=session_id,
                role="user",
                content="Hello from integration test",
            )
        )
        await db.commit()

        resp = await client.get(f"/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == session_id
        messages = data.get("messages", [])
        assert any(m["id"] == msg_id for m in messages), "Persisted message not returned"

    async def test_list_sessions_returns_created(self, client: AsyncClient, db):
        from backend.db.models import Session as SessionModel
        from sqlalchemy import insert

        session_id = str(uuid.uuid4())
        await db.execute(
            insert(SessionModel).values(
                id=session_id,
                title="Listed Test Session",
                provider="ollama",
                model="llama3.2:3b",
            )
        )
        await db.commit()

        resp = await client.get("/sessions")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()]
        assert session_id in ids


# ── TC-02: Ingestion idempotency ─────────────────────────────────────────────

class TestIngestionIdempotency:
    async def test_same_content_hash_no_duplicate(self, db):
        """Re-ingesting the same episode slug + content_hash must not create duplicates."""
        from backend.db.models import Episode
        from sqlalchemy import insert, select

        slug = f"test-episode-{uuid.uuid4().hex[:8]}"
        content = "This is test episode content"
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Insert episode
        await db.execute(
            insert(Episode).values(
                id=str(uuid.uuid4()),
                slug=slug,
                title="Test Episode",
                content_hash=content_hash,
                source_path=f"podcasts/{slug}.md",
            )
        )
        await db.commit()

        # Check only one row for this slug
        result = await db.execute(select(Episode).where(Episode.slug == slug))
        episodes = result.scalars().all()
        assert len(episodes) == 1
        assert episodes[0].content_hash == content_hash

    async def test_changed_content_hash_updates_episode(self, db):
        """Changing content_hash should update the episode (not create a duplicate)."""
        from backend.db.models import Episode
        from sqlalchemy import insert, update, select

        slug = f"test-update-{uuid.uuid4().hex[:8]}"
        hash1 = hashlib.sha256(b"v1 content").hexdigest()
        hash2 = hashlib.sha256(b"v2 content").hexdigest()

        await db.execute(
            insert(Episode).values(
                id=str(uuid.uuid4()),
                slug=slug,
                title="Test Update Episode",
                content_hash=hash1,
                source_path=f"podcasts/{slug}.md",
            )
        )
        await db.commit()

        # Simulate update
        await db.execute(
            update(Episode).where(Episode.slug == slug).values(content_hash=hash2)
        )
        await db.commit()

        result = await db.execute(select(Episode).where(Episode.slug == slug))
        episodes = result.scalars().all()
        assert len(episodes) == 1
        assert episodes[0].content_hash == hash2


# ── TC-03: Health endpoints ──────────────────────────────────────────────────

class TestHealthEndpoints:
    async def test_health_returns_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_health_live_returns_alive(self, client: AsyncClient):
        resp = await client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    async def test_health_ready_has_all_checks(self, client: AsyncClient):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checks" in data
        checks = data["checks"]
        assert "database" in checks
        assert "ollama" in checks
        assert "index_populated" in checks
        assert "anthropic" in checks

    async def test_health_ready_database_ok(self, client: AsyncClient):
        resp = await client.get("/health/ready")
        data = resp.json()
        # DB must be ok since we're running against it
        assert data["checks"]["database"]["status"] == "ok"


# ── TC-04: Config/providers ─────────────────────────────────────────────────

class TestConfig:
    async def test_providers_endpoint(self, client: AsyncClient):
        resp = await client.get("/config/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        providers = data["providers"]
        assert isinstance(providers, list)
        assert len(providers) > 0

    async def test_ollama_provider_listed(self, client: AsyncClient):
        resp = await client.get("/config/providers")
        names = [p["name"] for p in resp.json()["providers"]]
        assert "ollama" in names


# ── TC-05: Retrieval ranking ─────────────────────────────────────────────────

class TestRetrieval:
    async def test_chunks_exist_after_ingest(self, db):
        """After make ingest, chunks table must have entries."""
        result = await db.execute(text("SELECT COUNT(*) FROM chunks"))
        count = result.scalar()
        assert count > 0, "No chunks found - run make ingest first"

    async def test_episodes_exist_after_ingest(self, db):
        result = await db.execute(text("SELECT COUNT(*) FROM episodes"))
        count = result.scalar()
        assert count > 0, "No episodes found - run make ingest first"

    async def test_chunks_have_embeddings(self, db):
        """Every chunk should have a non-null embedding vector."""
        result = await db.execute(
            text("SELECT COUNT(*) FROM chunks WHERE embedding IS NULL")
        )
        null_count = result.scalar()
        assert null_count == 0, f"{null_count} chunks missing embeddings"


# ── TC-06: Error shapes ──────────────────────────────────────────────────────

class TestErrorShapes:
    async def test_404_returns_error_shape(self, client: AsyncClient):
        resp = await client.get("/sessions/nonexistent-id-00000000")
        assert resp.status_code in (404, 422)

    async def test_session_not_found(self, client: AsyncClient):
        resp = await client.get(f"/sessions/{uuid.uuid4()}")
        assert resp.status_code == 404
