"""Unit tests for the router."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

import pytest
import asyncio
from unittest.mock import AsyncMock
from backend.agents.router import route


class MockProvider:
    async def complete(self, messages, max_tokens=50, temperature=0):
        # Simulate LLM returning answer_with_sources for unknown queries
        return "answer_with_sources"


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestRouter:
    def test_ship30_patterns_match(self):
        ship30_messages = [
            "Write me a Ship 30 essay about user onboarding",
            "I want a Ship30 piece on growth loops",
            "Draft an essay about product strategy",
            "Can you write an article about this topic?",
            "Write an atomic essay on retention",
        ]
        provider = MockProvider()
        for msg in ship30_messages:
            result = run(route(msg, provider))
            assert result == "write_ship30_essay", f"Expected write_ship30_essay for: '{msg}', got: {result}"

    def test_artifact_patterns_match(self):
        artifact_messages = [
            "Create an artifact from this conversation",
            "Generate a document summarizing this",
            "I need a one-pager on this topic",
            "Create a memo about what we discussed",
        ]
        provider = MockProvider()
        for msg in artifact_messages:
            result = run(route(msg, provider))
            assert result == "create_artifact", f"Expected create_artifact for: '{msg}', got: {result}"

    def test_default_route_is_answer_with_sources(self):
        factual_messages = [
            "What did Molly Graham say about onboarding?",
            "How does Peter Sellis think about product decisions?",
            "Tell me about the growth loop concept",
            "What are the key takeaways from the talent density episode?",
        ]
        provider = MockProvider()
        for msg in factual_messages:
            result = run(route(msg, provider))
            assert result == "answer_with_sources", f"Expected answer_with_sources for: '{msg}', got: {result}"

    def test_ship30_takes_priority_over_artifact(self):
        """Ship 30 essay request with 'document' language should still route to ship30."""
        msg = "Write a Ship 30 essay document about retention"
        provider = MockProvider()
        result = run(route(msg, provider))
        assert result == "write_ship30_essay"

    def test_case_insensitive_matching(self):
        provider = MockProvider()
        result = run(route("SHIP 30 essay please", provider))
        assert result == "write_ship30_essay"
