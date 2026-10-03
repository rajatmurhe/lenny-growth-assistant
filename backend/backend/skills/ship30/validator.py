"""
Ship 30 for 30 essay validator.
Checks word count, hook, headings, bullets, takeaway, and citation validity.
"""
from __future__ import annotations

import re
from pydantic import BaseModel


class Ship30ValidationResult(BaseModel):
    passed: bool
    failures: list[str]
    word_count: int


def _count_words(text: str) -> int:
    return len(text.split())


def _count_headings(text: str) -> int:
    return len(re.findall(r'^#{1,3}\s+.+', text, re.MULTILINE))


def _has_bullets(text: str) -> bool:
    bullet_lines = re.findall(r'^[\-\*\•]\s+.+', text, re.MULTILINE)
    return len(bullet_lines) >= 2  # At least 2 bullet items


def _has_hook(text: str) -> bool:
    """First non-empty paragraph must be non-trivial (>20 words)."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        return False
    first_para = paragraphs[0]
    return len(first_para.split()) >= 15


def _has_takeaway(text: str) -> bool:
    """Final section or explicit takeaway marker."""
    text_lower = text.lower()
    takeaway_markers = [
        r'##\s*takeaway',
        r'##\s*the\s+takeaway',
        r'##\s*key\s+takeaway',
        r'\*\*takeaway',
        r'\*\*the\s+bottom\s+line',
        r'\*\*what\s+this\s+means',
        r'\*\*action\s+item',
    ]
    for marker in takeaway_markers:
        if re.search(marker, text_lower):
            return True
    # Fallback: last paragraph is at least 20 words and contains actionable language
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if paragraphs:
        last = paragraphs[-1].lower()
        actionable_words = ['you should', 'start', 'try', 'next time', 'remember', 'the key is', 'apply', 'ask yourself']
        if any(w in last for w in actionable_words) and len(last.split()) >= 20:
            return True
    return False


def _extract_citations(text: str) -> list[int]:
    return list(set(int(m) for m in re.findall(r'\[(\d+)\]', text)))


def validate_ship30_essay(
    essay: str,
    retrieved_chunk_ids: list[str],
    skill_config: dict,
) -> Ship30ValidationResult:
    """
    Validate a Ship 30 essay against the skill configuration.
    """
    validator_config = skill_config.get("validator", {})
    min_words = validator_config.get("min_words", 1100)
    max_words = validator_config.get("max_words", 1400)
    min_headings = validator_config.get("min_headings", 2)
    min_citations = validator_config.get("min_citations", 3)

    failures: list[str] = []

    # Word count
    word_count = _count_words(essay)
    if word_count < min_words:
        failures.append(f"Too short: {word_count} words (minimum {min_words})")
    elif word_count > max_words:
        failures.append(f"Too long: {word_count} words (maximum {max_words})")

    # Hook
    if validator_config.get("require_hook", True) and not _has_hook(essay):
        failures.append("Hook missing or too brief (first paragraph must be >= 15 words)")

    # Headings
    heading_count = _count_headings(essay)
    if heading_count < min_headings:
        failures.append(f"Too few headings: {heading_count} (minimum {min_headings}). Add ## section headings.")

    # Bullets
    if validator_config.get("require_bullets", True) and not _has_bullets(essay):
        failures.append("No bullet list found. Add at least 2 bullet points (- item).")

    # Takeaway
    if validator_config.get("require_takeaway", True) and not _has_takeaway(essay):
        failures.append("Takeaway missing. End with a ## Takeaway section or bold action item.")

    # Citations
    if validator_config.get("require_citations", True):
        citations = _extract_citations(essay)
        if len(citations) < min_citations:
            failures.append(f"Too few citations: {len(citations)} (minimum {min_citations}). Add [n] inline citations.")

        # Check for out-of-range citations
        max_valid = len(retrieved_chunk_ids)
        invalid = [c for c in citations if c < 1 or c > max_valid]
        if invalid:
            failures.append(f"Invalid citation indices: {invalid}. Only [1] through [{max_valid}] are valid.")

    return Ship30ValidationResult(
        passed=len(failures) == 0,
        failures=failures,
        word_count=word_count,
    )
