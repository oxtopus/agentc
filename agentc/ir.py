from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SkillSection:
    heading: str
    level: int
    body: str
    conditional: bool
    refs: list[str] = field(default_factory=list)


@dataclass
class ParsedSkill:
    name: str
    description: str
    allowed_tools: list[str]
    source_dir: Path
    body: str
    sections: list[SkillSection]
    references: list[Path]
    rules: list[Path]
    sibling_refs: list[str]


@dataclass
class CompileOpts:
    name: str
    out_dir: Path
    harnesses: list[str]
    force: bool = False
