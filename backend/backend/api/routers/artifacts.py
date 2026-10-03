"""Artifacts router: retrieve artifacts and their versions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Artifact
from backend.db.session import get_db

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _artifact_to_dict(a: Artifact, include_content: bool = True) -> dict:
    d = {
        "id": str(a.id),
        "session_id": str(a.session_id),
        "message_id": str(a.message_id) if a.message_id else None,
        "type": a.type,
        "title": a.title,
        "version": a.version,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
    if include_content:
        d["content"] = a.content
        d["sanitized_content"] = a.sanitized_content
    return d


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Artifact).where(Artifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return _artifact_to_dict(artifact)


@router.get("/{artifact_id}/versions")
async def list_artifact_versions(artifact_id: str, db: AsyncSession = Depends(get_db)):
    """Return all versions of an artifact (by parent chain)."""
    # Get the requested artifact first to find its root
    result = await db.execute(
        select(Artifact).where(Artifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Find root (no parent_id)
    root_id = artifact_id
    current = artifact
    while current.parent_id:
        result = await db.execute(
            select(Artifact).where(Artifact.id == str(current.parent_id))
        )
        parent = result.scalar_one_or_none()
        if not parent:
            break
        current = parent
        root_id = str(current.id)

    # Get all versions sharing the same root (by session + title)
    all_result = await db.execute(
        select(Artifact)
        .where(
            Artifact.session_id == artifact.session_id,
            Artifact.title == artifact.title,
        )
        .order_by(Artifact.version.asc())
    )
    versions = all_result.scalars().all()
    return [_artifact_to_dict(v, include_content=False) for v in versions]
