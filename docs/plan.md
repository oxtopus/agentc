# agentc — Implementation Plan

**Status:** v0 implemented; superseded by `README.md` and `SKILL.md`. Isolation is provided by `claude --bare` rather than a per-agent `CLAUDE_HOME`/`settings.json` scaffold (see `agentc/adapters/claude_code.py`).

## Context

Skills (SKILL.md + frontmatter + references/rules) live inside an agent harness like Claude Code and are loaded into a session on demand. They're useful, but they're not portable — you can't hand someone "the firecrawl skill as a standalone tool" without also handing them the harness, settings, hooks, and ambient state.

`agentc` makes a skill into a real artifact. It reads a SKILL.md and emits a **self-contained, git-tracked agent project** that runs on its own. Initial output target is Claude Code (with an isolated `CLAUDE_HOME`); OpenCode, Codex, and raw Claude API are adapters that ship later, behind the same interface.

Naming reads as a compiler (`gcc`/`rustc`/`tsc` → `agentc`). The "compiler" framing is load-bearing — it sets the long-term direction: not just "copy the skill into a wrapper" but eventually **decompose the skill into smaller code units** so conditional/diverging paths become real branches and token-heavy boilerplate gets extracted. v0 is a pass-through copy; the IR must leave room for that decomposition to grow into.

## Recommended approach

### Project location and scaffold reconciliation

Rehome `/home/austin/agent-harness/` → `/home/austin/agentc/`. The existing `harness/{agent,llm,mcp_servers,memory,plugins,tools}` tree describes a *single pluggable harness* — wrong mental model for a compiler that emits whole harnesses. **Delete the `harness/` tree.** Keep the `.venv/` (typer installed already).

### Repo layout

```
/home/austin/agentc/
  SKILL.md                # the agentc skill itself (root)
  README.md
  pyproject.toml          # single source of truth (anthropic, typer, python-frontmatter, jinja2)
  .gitignore              # .venv/, __pycache__, **/.env
  .venv/                  # reused from agent-harness
  agentc/                 # the CLI package
    __init__.py
    __main__.py           # python -m agentc
    cli.py                # typer app
    ingest.py             # SkillParser
    ir.py                 # dataclasses for the IR (see below)
    registry.py           # discovers compiled agents under repo root
    adapters/
      __init__.py         # HarnessAdapter ABC, ADAPTERS registry
      claude_code.py      # default adapter
      opencode.py         # later
      codex.py            # later
      raw_api.py          # later
    templates/
      claude_code/
      common/
    util.py               # slugify, fs helpers
  .agentc/
    manifest.json         # list of compiled agents
  <compiled-agent>/       # sibling subdirs (one per compiled agent)
```

One git repo at root. Compiled agents are committed siblings.

### Skill ingestion + IR

`agentc/ingest.py` parses `<skill-dir>/SKILL.md` plus optional `references/` and `rules/`. Dataclasses in `agentc/ir.py`:

```python
@dataclass
class SkillSection:
    heading: str                    # e.g. "## When to Load References"
    body: str
    conditional: bool               # heuristic: starts with "If ...", "When ..."
    refs: list[str]                 # links/paths found in this section

@dataclass
class ParsedSkill:
    name: str
    description: str
    allowed_tools: list[str]
    source_dir: Path
    sections: list[SkillSection]    # body decomposed into sections
    references: list[Path]          # files under references/
    rules: list[Path]               # files under rules/
    sibling_refs: list[str]         # ../<name>/SKILL.md links found (recorded, NOT followed)
```

Critical: the body is split into `SkillSection`s at heading boundaries with conditional flagging. v0 emits all sections as one document — but the IR shape unlocks the future decomposition goal (each section becomes a code branch, conditionals become real if-statements at the harness layer).

**Sibling bundling: none.** Cross-skill `../sibling/SKILL.md` links are *recorded* in `sibling_refs` for future use and reported as warnings, but not copied. The compiled agent owns only the root skill.

### Harness adapter interface

```python
class HarnessAdapter(ABC):
    name: str
    @abstractmethod
    def emit(self, skill: ParsedSkill, out_dir: Path, opts: CompileOpts) -> None: ...
    @abstractmethod
    def entrypoint_cmd(self, agent_dir: Path) -> list[str]: ...

ADAPTERS = {"claude-code": ClaudeCodeAdapter}  # opencode/codex/raw-api added later
```

Each adapter writes to its own subdirectory inside the compiled-agent dir (`claude-code/`, `opencode/`, ...) so future multi-target compiles don't collide. Shared assets (`skill/`, `README.md`, `.env.example`) live at the compiled-agent root.

### Compiled-agent layout

```
/home/austin/agentc/<agent-name>/
  README.md                # auto-generated; name, description, run instructions
  .env.example             # ANTHROPIC_API_KEY plus any tool-specific keys inferred from allowed-tools
  .gitignore
  agent.toml               # source_path, source_hash, harnesses[], compiled_at
  skill/                   # hard copy of the source skill (input only; never read back)
    SKILL.md
    references/...
    rules/...
  claude-code/             # default adapter output
    .claude/
      settings.json        # permissions from allowed-tools; model: claude-opus-4-7
    skills/<name>/         # second copy of skill, structured how Claude Code wants it
    run.sh                 # CLAUDE_HOME=$(pwd)/.claude exec claude --skill <name> "$@"
```

`run.sh` sets an **isolated `CLAUDE_HOME`** pointing at the compiled agent's `.claude/` so global settings/hooks are not inherited.

`agent.toml` records `source_path` and `source_hash`. `agentc update` re-parses the source and warns if the hash differs from what was compiled; default behavior is hard-overwrite of generated files, with `.env` and a `[user_overrides]` block in `agent.toml` left untouched.

### CLI surface (`agentc/cli.py`)

```
agentc init [path]                         # scaffold monorepo + git init
agentc compile <skill-path>                # default emits claude-code only
        [--harness claude-code|...]        # repeatable; --harness all for everything
        [--name <slug>]                    # defaults to skill name (slugified)
        [--out <dir>]                      # defaults to /home/austin/agentc
        [--force]
agentc list                                # table from .agentc/manifest.json
agentc run <name>                          # exec compiled agent's run.sh
agentc update <name>                       # re-emit; preserves .env + user_overrides
agentc validate <skill-path>               # parse + print IR; no writes
agentc remove <name>                       # delete subdir + update manifest
```

### agentc SKILL.md (at repo root)

```yaml
---
name: agentc
description: |
  Compile an agent skill into a standalone, runnable agent project. Use
  when the user says "compile this skill", "make a standalone harness for
  <skill>", "wrap <skill> as a runnable agent", "package this skill", or
  "build an agent from <skill>". Do NOT use for authoring new skills.
allowed-tools:
  - Bash(agentc *)
  - Bash(python -m agentc *)
---
```

Symlink `/home/austin/.agents/skills/agentc/SKILL.md → /home/austin/agentc/SKILL.md` so the skill loads in any Claude Code session.

### Defaults locked in

- **Default harness:** Claude Code only when `--harness` is omitted.
- **Isolation:** hard copy of skill + isolated `CLAUDE_HOME` per compiled agent.
- **Sibling deps:** not bundled. Recorded only.
- **Model:** `claude-opus-4-7` baked into emitted `settings.json` (matches user's global default).
- **Distribution:** `pipx install -e /home/austin/agentc` so `agentc` lands on `PATH`. `python -m agentc` works as a fallback.

## Critical files to create

- `/home/austin/agentc/SKILL.md`
- `/home/austin/agentc/pyproject.toml`
- `/home/austin/agentc/README.md`
- `/home/austin/agentc/agentc/cli.py`
- `/home/austin/agentc/agentc/ingest.py`
- `/home/austin/agentc/agentc/ir.py`
- `/home/austin/agentc/agentc/adapters/__init__.py`
- `/home/austin/agentc/agentc/adapters/claude_code.py`
- `/home/austin/agentc/agentc/templates/claude_code/settings.json.j2`
- `/home/austin/agentc/agentc/templates/common/README.md.j2`

## Files/scaffolding to remove

- `/home/austin/agent-harness/harness/{agent,llm,mcp_servers,memory,plugins,tools}/` — delete entire tree
- Rename `/home/austin/agent-harness/` → `/home/austin/agentc/`
- Keep `.venv/` (typer already installed)

## Existing utilities to reuse

- `.venv/` with `typer` already installed
- `python-frontmatter` (add to pyproject) — handles SKILL.md YAML parsing without reinvention
- `anthropic` Python SDK — only needed once `raw-api` adapter ships (out of scope for v0)
- User's existing skill examples at `/home/austin/.agents/skills/` (firecrawl, find-skills, open-websearch) serve as ingestion test fixtures

## Verification

1. **Bootstrap:** rename `agent-harness/` → `agentc/`, drop the `harness/` tree, install `pyproject.toml`, run `pipx install -e /home/austin/agentc`. `agentc --help` should list every command.
2. **Validate (no-write):** `agentc validate /home/austin/.agents/skills/firecrawl` — prints parsed IR (name, description, allowed_tools, section count, recorded sibling_refs) without touching disk.
3. **Compile:** `agentc compile /home/austin/.agents/skills/firecrawl`. Confirm `/home/austin/agentc/firecrawl/` exists with `skill/`, `claude-code/`, `agent.toml`, `README.md`, `.env.example`. Confirm `agent.toml` records `source_hash`.
4. **Isolation check:** `cat /home/austin/agentc/firecrawl/claude-code/run.sh` — must set `CLAUDE_HOME` to the local `.claude/`. Run it; confirm Claude Code launches without the user's global SessionStart/PreToolUse hooks firing.
5. **Roundtrip:** edit the source skill, run `agentc update firecrawl`, confirm regenerated files reflect the edit and that `.env` (if present) is preserved.
6. **Skill discovery:** in a fresh Claude Code session, ask "compile the open-websearch skill". The agentc skill should trigger and the CLI should run.
7. **IR forward-compat:** `agentc validate` on a skill with multiple `## When ...` headings produces sections with `conditional=True`. This is the seam for future skill decomposition; no behavior depends on it yet, but the field must be populated.
