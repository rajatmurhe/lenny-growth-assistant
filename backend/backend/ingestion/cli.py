"""
Ingestion CLI: python -m backend.ingestion.cli ingest

Clones/pulls the transcript repository if needed, then runs the full ingestion pipeline.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time

from backend.config import settings
from backend.db.session import AsyncSessionLocal
from backend.ingestion.pipeline import run_ingestion
from backend.providers.factory import get_embed_provider


def _clone_or_pull_repo(transcript_dir: str, repo_url: str) -> None:
    """Clone the transcript repo if not present, or pull if already cloned."""
    if os.path.exists(os.path.join(transcript_dir, "index.json")):
        print(f"→ Transcript repo already present at {transcript_dir}")
        print("  Pulling latest changes...")
        result = subprocess.run(
            ["git", "-C", transcript_dir, "pull", "--ff-only"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  {result.stdout.strip() or 'Already up to date.'}")
        else:
            print(f"  Warning: git pull failed: {result.stderr.strip()}")
            print("  Continuing with existing transcripts.")
    else:
        print(f"→ Cloning transcript repo from {repo_url}")
        print(f"  Into: {transcript_dir}")
        os.makedirs(os.path.dirname(transcript_dir), exist_ok=True)
        result = subprocess.run(
            ["git", "clone", "--depth=1", repo_url, transcript_dir],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git clone failed:\n{result.stderr}")
        print("  Cloned successfully.")


async def _run() -> None:
    # Clone/pull transcript repo
    _clone_or_pull_repo(settings.TRANSCRIPT_DIR, settings.TRANSCRIPT_REPO_URL)

    # Run ingestion pipeline
    print("\n→ Starting ingestion pipeline...")
    print(f"  Transcript dir: {settings.TRANSCRIPT_DIR}")
    print(f"  Embed model: {settings.OLLAMA_EMBED_MODEL}")
    print("  This may take several minutes for the first run.\n")

    t0 = time.monotonic()

    async with AsyncSessionLocal() as session:
        embed_provider = get_embed_provider(settings)
        result = await run_ingestion(session, embed_provider, settings)

    elapsed = time.monotonic() - t0

    print(f"\n{'✅' if result.status == 'completed' else '❌'} Ingestion {result.status}")
    print(f"  Episodes processed: {result.episodes_processed}")
    print(f"  Chunks created: {result.chunks_created}")
    print(f"  Time elapsed: {elapsed:.1f}s")

    if result.error_message:
        print(f"  Error: {result.error_message}")
        sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] != "ingest":
        print("Usage: python -m backend.ingestion.cli ingest")
        sys.exit(1)

    asyncio.run(_run())


if __name__ == "__main__":
    main()
