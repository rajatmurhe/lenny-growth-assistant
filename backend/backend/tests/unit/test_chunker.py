"""Unit tests for the transcript chunker."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

import pytest
from backend.ingestion.chunker import chunk_episode
from backend.ingestion.loader import EpisodeRaw
from datetime import date


SAMPLE_TRANSCRIPT = """---
title: "Test Episode"
date: "2024-01-01"
guest: "Test Guest"
---

**Lenny Rachitsky** (00:00:00):
Welcome to the podcast. Today we're talking about product management.

**Test Guest** (00:00:10):
Thanks for having me. Product management is a fascinating topic. Let me share what I've learned
over the past decade of building products at various companies.
The key insight is that great product managers are obsessed with understanding user problems.

**Lenny Rachitsky** (00:01:30):
Can you give a specific example of how you've used this in practice?

**Test Guest** (00:01:45):
Absolutely. At my last company, we noticed users were churning after 30 days. We did user interviews
and discovered they were confused about the core value prop. We fixed the onboarding flow and
retention improved dramatically. The lesson was: never assume you know why users behave the way they do.
Always go back to the source. Always talk to real users.

**Lenny Rachitsky** (00:03:00):
That's a really powerful example. How does this apply to AI-native products?

**Test Guest** (00:03:15):
With AI products, the challenge is even greater because users don't know what's possible.
You have to do a lot of education alongside product design. The best AI products I've seen
make the AI feel like a natural extension of the user's workflow, not a bolt-on feature.
""" * 3  # Repeat to have enough content for multiple chunks


def _make_episode(text: str) -> EpisodeRaw:
    import hashlib
    return EpisodeRaw(
        slug="test-episode",
        title="Test Episode",
        guest="Test Guest",
        published_at=date(2024, 1, 1),
        source_path="/tmp/test.md",
        post_url=None,
        word_count=len(text.split()),
        raw_text=text,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


class TestChunkEpisode:
    def test_produces_multiple_chunks(self):
        episode = _make_episode(SAMPLE_TRANSCRIPT)
        chunks = chunk_episode(episode, max_tokens=200, overlap_tokens=20)
        assert len(chunks) >= 2, f"Expected multiple chunks, got {len(chunks)}"

    def test_ordinals_are_sequential(self):
        episode = _make_episode(SAMPLE_TRANSCRIPT)
        chunks = chunk_episode(episode, max_tokens=200, overlap_tokens=20)
        ordinals = [c.ordinal for c in chunks]
        assert ordinals == list(range(1, len(ordinals) + 1)), f"Ordinals not sequential: {ordinals}"

    def test_all_chunks_have_slug(self):
        episode = _make_episode(SAMPLE_TRANSCRIPT)
        chunks = chunk_episode(episode)
        for chunk in chunks:
            assert chunk.episode_slug == "test-episode"

    def test_token_counts_within_bounds(self):
        episode = _make_episode(SAMPLE_TRANSCRIPT)
        max_tokens = 300
        chunks = chunk_episode(episode, max_tokens=max_tokens, overlap_tokens=30)
        # Allow some buffer over max_tokens (one speaker turn might exceed the limit)
        for chunk in chunks[:-1]:  # Last chunk may be shorter
            assert chunk.token_count <= max_tokens * 2, (
                f"Chunk {chunk.ordinal} has {chunk.token_count} tokens, "
                f"expected <= {max_tokens * 2}"
            )

    def test_text_content_preserved(self):
        episode = _make_episode(SAMPLE_TRANSCRIPT)
        chunks = chunk_episode(episode)
        combined = " ".join(c.text for c in chunks)
        # Key phrases from the transcript should appear somewhere in the chunks
        assert "product management" in combined.lower()
        assert "user" in combined.lower()

    def test_speaker_detected(self):
        episode = _make_episode(SAMPLE_TRANSCRIPT)
        chunks = chunk_episode(episode)
        speakers = [c.speaker for c in chunks if c.speaker]
        assert len(speakers) > 0, "No speakers detected in any chunk"
        # At least one chunk should identify a speaker
        assert any("Guest" in s or "Rachitsky" in s for s in speakers)

    def test_handles_empty_text(self):
        episode = _make_episode("") 
        chunks = chunk_episode(episode)
        assert chunks == [] or len(chunks) == 1  # Empty or single empty chunk

    def test_single_chunk_for_short_text(self):
        short_text = "**Speaker** (00:00:00):\nThis is a very short episode with minimal content."
        episode = _make_episode(short_text)
        chunks = chunk_episode(episode, max_tokens=500)
        assert len(chunks) == 1
