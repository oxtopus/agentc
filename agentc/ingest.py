from __future__ import annotations

import re
from pathlib import Path

import frontmatter

from agentc.ir import ParsedSkill, SkillSection

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SIBLING_RE = re.compile(r"\.\./([A-Za-z0-9_-]+)/SKILL\.md")
CONDITIONAL_PREFIXES = ("if ", "when ", "use when", "use this", "do not", "don't")


def _split_sections(body: str) -> list[SkillSection]:
    matches = list(HEADING_RE.finditer(body))
    sections: list[SkillSection] = []
    if not matches:
        return [SkillSection(heading="", level=0, body=body.strip(), conditional=False)]
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        heading = m.group(2).strip()
        level = len(m.group(1))
        first_line = content.split("\n", 1)[0].strip().lower()
        conditional = (
            heading.lower().startswith(("when ", "if "))
            or any(first_line.startswith(p) for p in CONDITIONAL_PREFIXES)
        )
        refs = LINK_RE.findall(content)
        sections.append(
            SkillSection(
                heading=heading,
                level=level,
                body=content,
                conditional=conditional,
                refs=refs,
            )
        )
    return sections


def _list_files(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return sorted(p for p in path.rglob("*") if p.is_file())


def parse(skill_path: Path) -> ParsedSkill:
    skill_path = skill_path.resolve()
    skill_md = skill_path / "SKILL.md"
    if not skill_md.is_file():
        raise FileNotFoundError(f"No SKILL.md at {skill_md}")

    post = frontmatter.load(skill_md)
    meta = post.metadata
    body = post.content

    name = str(meta.get("name") or skill_path.name).strip()
    description = str(meta.get("description") or "").strip()
    raw_tools = meta.get("allowed-tools") or []
    if isinstance(raw_tools, str):
        allowed_tools = [t.strip() for t in raw_tools.splitlines() if t.strip()]
    else:
        allowed_tools = [str(t).strip() for t in raw_tools if str(t).strip()]

    sections = _split_sections(body)
    references = _list_files(skill_path / "references")
    rules = _list_files(skill_path / "rules")
    sibling_refs = sorted(set(SIBLING_RE.findall(body)))

    return ParsedSkill(
        name=name,
        description=description,
        allowed_tools=allowed_tools,
        source_dir=skill_path,
        body=body,
        sections=sections,
        references=references,
        rules=rules,
        sibling_refs=sibling_refs,
    )
