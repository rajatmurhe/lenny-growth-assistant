"""Unit tests for the citation validator."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from backend.agents.citation_validator import validate_citations


class TestCitationValidator:
    def test_valid_citations_detected(self):
        text = "Molly Graham argued that clarity prevents burnout [1]. She also said AI changes things [2]."
        chunk_ids = ["chunk-a", "chunk-b", "chunk-c"]
        result = validate_citations(text, chunk_ids)
        assert 1 in result.valid_citations
        assert 2 in result.valid_citations
        assert len(result.invalid_citations) == 0
        assert result.is_valid is True

    def test_out_of_range_citation_is_invalid(self):
        text = "Some claim [5] that seems valid."
        chunk_ids = ["chunk-a", "chunk-b", "chunk-c"]  # Only 3 chunks
        result = validate_citations(text, chunk_ids)
        assert 5 in result.invalid_citations
        assert result.is_valid is False

    def test_no_citations_is_valid(self):
        """A response with no citations is structurally valid (may be flagged elsewhere)."""
        text = "The episode discussed product management at length."
        chunk_ids = ["chunk-a", "chunk-b"]
        result = validate_citations(text, chunk_ids)
        assert result.is_valid is True
        assert len(result.valid_citations) == 0
        assert len(result.invalid_citations) == 0

    def test_mixed_valid_and_invalid(self):
        text = "First claim [1]. Second claim [2]. Third claim [10]."
        chunk_ids = ["c1", "c2", "c3"]
        result = validate_citations(text, chunk_ids)
        assert 1 in result.valid_citations
        assert 2 in result.valid_citations
        assert 10 in result.invalid_citations
        assert result.is_valid is False

    def test_duplicate_citations_handled(self):
        text = "Claim [1] and also [1] again. Different claim [2]."
        chunk_ids = ["c1", "c2"]
        result = validate_citations(text, chunk_ids)
        assert result.is_valid is True
        # Should not double-count
        assert len(result.invalid_citations) == 0

    def test_zero_citation_is_invalid(self):
        """Citation [0] is invalid (1-indexed)."""
        text = "Some claim [0]."
        chunk_ids = ["c1", "c2"]
        result = validate_citations(text, chunk_ids)
        assert 0 in result.invalid_citations
        assert result.is_valid is False

    def test_empty_response(self):
        result = validate_citations("", ["c1"])
        assert result.is_valid is True

    def test_empty_chunk_list(self):
        """Any citation is invalid if no chunks were retrieved."""
        text = "Some claim [1]."
        result = validate_citations(text, [])
        assert 1 in result.invalid_citations
        assert result.is_valid is False
