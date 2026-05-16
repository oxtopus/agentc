from pathlib import Path

from agentc.ingest import parse

FIXTURES = Path(__file__).parent / "fixtures" / "skills"


def test_parse_basic():
    skill = parse(FIXTURES / "basic")
    assert skill.name == "basic"
    assert skill.allowed_tools == ["Bash(echo *)"]
    assert any(s.heading == "Commands" for s in skill.sections)
    assert skill.references == []
    assert skill.sibling_refs == []


def test_parse_conditional_detection():
    skill = parse(FIXTURES / "conditional")
    by_heading = {s.heading: s for s in skill.sections}
    assert by_heading["When the user asks X"].conditional
    assert by_heading["Helpers"].conditional
    assert not by_heading["Always available"].conditional


def test_parse_sibling_refs():
    skill = parse(FIXTURES / "with-refs")
    assert "other" in skill.sibling_refs
    assert len(skill.references) >= 1
    assert len(skill.rules) >= 1
