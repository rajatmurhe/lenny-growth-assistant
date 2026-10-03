"""Unit tests for the Ship 30 essay validator."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

import yaml
from backend.skills.ship30.validator import validate_ship30_essay


def _load_skill_config():
    skill_yaml = os.path.join(
        os.path.dirname(__file__),
        "../../skills/ship30/skill.yaml"
    )
    with open(skill_yaml) as f:
        return yaml.safe_load(f)


def _make_valid_essay(word_count: int = 1200) -> str:
    """Generate a structurally valid essay of approximately word_count words."""
    hook = "Why do most product managers fail at user research? They ask the wrong questions. The issue is not effort or intelligence — it is a fundamental misunderstanding of what user research is actually for."
    
    heading1 = "\n\n## The Research Trap Most PMs Fall Into\n\n"
    para1 = "Peter Sellis from Discord spent years watching PMs conduct research that led nowhere [1]. The problem was not effort but method. Teams would run surveys when they needed conversations, and focus groups when they needed observation. This misalignment between method and question type is the root cause of most research failure."
    
    heading2 = "\n\n## What Top PMs Do Differently\n\n"
    para2 = "Molly Graham shared a framework from her time at Google and Facebook [2]. The best PMs she worked with shared three habits. First, they always started with the user's goal, not the product feature. Second, they talked to users weekly, not quarterly. Third, they brought engineers to user interviews, not just PMs."
    
    bullets = "\n\n**The three habits of evidence-driven PMs:**\n- Weekly user conversations, not quarterly surveys [3]\n- Engineers in the room during user research [4]\n- Written summaries distributed within 24 hours [5]\n\n"
    
    heading3 = "\n\n## The Evidence That Changed My Mind\n\n"
    para3 = "Adam Ward's experience at Cursor illustrates this perfectly [3]. His team discovered that their highest-performing employees were not the ones with the best technical skills. They were the ones most obsessed with understanding what users actually needed. This obsession cannot be taught in a hiring process. It must be screened for deliberately."
    
    takeaway = "\n\n## Takeaway\n\n**Start this week**: Schedule one user interview for next Tuesday. Not to validate a feature. Just to listen. Bring your notes to your next product review. Watch how the conversation changes."
    
    base = hook + heading1 + para1 + heading2 + para2 + bullets + heading3 + para3 + takeaway
    
    # Pad to target word count if needed
    current = len(base.split())
    if current < word_count:
        padding_needed = word_count - current
        filler = " ".join(["The evidence shows that consistent user research fundamentally improves product decisions and team alignment."] * (padding_needed // 12 + 1))
        base += "\n\n" + " ".join(filler.split()[:padding_needed])
    
    return base


SKILL_CONFIG = _load_skill_config()
CHUNK_IDS = ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10"]


class TestShip30Validator:
    def test_valid_essay_passes(self):
        essay = _make_valid_essay(1200)
        result = validate_ship30_essay(essay, CHUNK_IDS, SKILL_CONFIG)
        assert result.passed, f"Expected pass but got failures: {result.failures}"
        assert 1100 <= result.word_count <= 1400

    def test_too_short_fails(self):
        essay = _make_valid_essay(500)
        result = validate_ship30_essay(essay, CHUNK_IDS, SKILL_CONFIG)
        assert not result.passed
        assert any("short" in f.lower() or "word" in f.lower() for f in result.failures)

    def test_too_long_fails(self):
        essay = _make_valid_essay(2000)
        result = validate_ship30_essay(essay, CHUNK_IDS, SKILL_CONFIG)
        assert not result.passed
        assert any("long" in f.lower() or "word" in f.lower() for f in result.failures)

    def test_no_headings_fails(self):
        # Essay without ## headings
        essay = _make_valid_essay(1200).replace("## ", "").replace("\n\n## ", "\n\n")
        result = validate_ship30_essay(essay, CHUNK_IDS, SKILL_CONFIG)
        assert not result.passed
        assert any("heading" in f.lower() for f in result.failures)

    def test_no_citations_fails(self):
        # Remove all [n] citations
        import re
        essay = re.sub(r'\[\d+\]', '', _make_valid_essay(1200))
        result = validate_ship30_essay(essay, CHUNK_IDS, SKILL_CONFIG)
        assert not result.passed
        assert any("citation" in f.lower() for f in result.failures)

    def test_invalid_citation_fails(self):
        # Use citation [99] which is out of range
        essay = _make_valid_essay(1200) + " Final claim [99]."
        result = validate_ship30_essay(essay, ["c1", "c2"], SKILL_CONFIG)  # Only 2 chunks
        assert not result.passed
        assert any("99" in f or "invalid" in f.lower() for f in result.failures)

    def test_word_count_reported_correctly(self):
        essay = _make_valid_essay(1200)
        result = validate_ship30_essay(essay, CHUNK_IDS, SKILL_CONFIG)
        assert abs(result.word_count - len(essay.split())) <= 5

    def test_no_bullets_fails(self):
        # Remove bullet list
        essay = _make_valid_essay(1200).replace("- ", "  ")
        result = validate_ship30_essay(essay, CHUNK_IDS, SKILL_CONFIG)
        assert not result.passed
        assert any("bullet" in f.lower() for f in result.failures)
