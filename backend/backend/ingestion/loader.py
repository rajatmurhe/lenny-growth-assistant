from pydantic import BaseModel
from typing import Optional
from datetime import date
import json
import os
import hashlib
import re


class EpisodeRaw(BaseModel):
    slug: str
    title: str
    guest: Optional[str]
    published_at: Optional[date]
    source_path: str
    post_url: Optional[str]
    word_count: Optional[int]
    raw_text: str
    content_hash: str


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter block (--- ... ---) from markdown text."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def load_corpus(transcript_dir: str) -> list[EpisodeRaw]:
    """Read index.json + all podcast markdown files."""
    index_path = os.path.join(transcript_dir, "index.json")
    if not os.path.exists(index_path):
        raise FileNotFoundError(
            f"index.json not found at {index_path}. "
            "Run 'make ingest' to clone the transcript repository."
        )

    with open(index_path) as f:
        data = json.load(f)

    # index.json has a "podcasts" key (schema_version 2.0)
    podcast_entries = data.get("podcasts", data.get("episodes", []))

    episodes: list[EpisodeRaw] = []

    for ep in podcast_entries:
        filename = ep.get("filename", "")
        # filename is like "podcasts/molly-graham-2.md"
        slug = os.path.splitext(os.path.basename(filename))[0]
        source_path = os.path.join(transcript_dir, filename)

        raw_text = ""
        if os.path.exists(source_path):
            with open(source_path, encoding="utf-8") as tf:
                raw_text = tf.read()
        else:
            # Try direct path
            alt_path = os.path.join(transcript_dir, "podcasts", f"{slug}.md")
            if os.path.exists(alt_path):
                source_path = alt_path
                with open(source_path, encoding="utf-8") as tf:
                    raw_text = tf.read()

        if not raw_text:
            continue  # Skip missing files

        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        episodes.append(
            EpisodeRaw(
                slug=slug,
                title=ep.get("title", slug),
                guest=ep.get("guest"),
                published_at=_parse_date(ep.get("date")),
                source_path=source_path,
                post_url=ep.get("post_url"),
                word_count=ep.get("word_count"),
                raw_text=raw_text,
                content_hash=content_hash,
            )
        )

    return episodes
