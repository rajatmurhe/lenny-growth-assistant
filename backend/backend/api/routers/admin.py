"""Admin router: trigger and monitor ingestion runs."""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import IngestionRun
from backend.db.session import get_db
from backend.ingestion.pipeline import run_ingestion
from backend.providers.factory import get_embed_provider

router = APIRouter(prefix="/admin", tags=["admin"])

# In-memory tracker of running ingestion (simple, single-instance)
_active_run_id: str | None = None


async def _run_ingestion_background(run_id: str, db_url: str):
    """Run ingestion in background, update IngestionRun status."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(db_url)
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        # Update status to running
        result = await session.execute(
            select(IngestionRun).where(IngestionRun.id == run_id)
        )
        run = result.scalar_one_or_none()

        try:
            embed_provider = get_embed_provider(settings)
            ingest_result = await run_ingestion(session, embed_provider, settings)

            if run:
                from datetime import datetime
                run.status = ingest_result.status
                run.episodes_processed = ingest_result.episodes_processed
                run.chunks_created = ingest_result.chunks_created
                run.completed_at = datetime.utcnow()
                run.error_message = ingest_result.error_message
                await session.commit()
        except Exception as e:
            if run:
                from datetime import datetime
                run.status = "failed"
                run.error_message = str(e)
                run.completed_at = datetime.utcnow()
                await session.commit()
        finally:
            global _active_run_id
            _active_run_id = None

    await engine.dispose()


@router.post("/ingest")
async def trigger_ingest(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger transcript ingestion pipeline. Returns run_id to track progress."""
    global _active_run_id
    if _active_run_id:
        return {"run_id": _active_run_id, "status": "already_running"}

    run_id = str(uuid.uuid4())
    _active_run_id = run_id

    run = IngestionRun(id=run_id, status="running")
    db.add(run)
    await db.commit()

    background_tasks.add_task(
        _run_ingestion_background,
        run_id,
        settings.DATABASE_URL,
    )

    return {"run_id": run_id, "status": "started"}


@router.get("/ingest/{run_id}")
async def get_ingest_status(run_id: str, db: AsyncSession = Depends(get_db)):
    """Get status of an ingestion run."""
    result = await db.execute(
        select(IngestionRun).where(IngestionRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        return {"error": "Run not found"}

    return {
        "run_id": run_id,
        "status": run.status,
        "episodes_processed": run.episodes_processed,
        "chunks_created": run.chunks_created,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
