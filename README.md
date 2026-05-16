# agentc

Compile an agent skill into a standalone, runnable agent project.

`agentc` reads a skill (a `SKILL.md` with YAML frontmatter, plus optional `references/` and `rules/` subdirectories) and emits a self-contained agent project that runs on its own. The compiled agent lives as a sibling subdirectory of this repo and is git-tracked as part of the monorepo.

Initial output target is Claude Code (run via `--bare`, which skips global hooks, auto-memory, plugin sync, and `CLAUDE.md` auto-discovery). OpenCode, Codex, and raw Claude API adapters will follow.

## Why

Skills live inside an agent harness and load on demand. They are useful but not portable — you can't hand someone "the firecrawl skill" as a standalone tool without also handing them the harness, settings, hooks, and ambient state. `agentc` turns a skill into a real artifact.

The name reads as a compiler (`gcc` / `rustc` / `tsc` → `agentc`). The framing is load-bearing: today this is a pass-through copy of the skill into a wrapper; the longer-term goal is to **decompose a skill into smaller code units** so conditional/diverging paths become real branches and token-heavy boilerplate gets extracted.

## Install

```bash
git clone <repo-url> ~/agentc && cd ~/agentc
pipx install -e .
```

Or run via the package directly:

```bash
python -m agentc --help
```

## Usage

```bash
agentc validate /home/austin/.agents/skills/firecrawl    # parse + print IR
agentc compile  /home/austin/.agents/skills/firecrawl    # emit compiled agent
agentc list
agentc run firecrawl
agentc update firecrawl
agentc remove firecrawl
```

## Layout

```
/home/austin/agentc/
  SKILL.md              # the agentc Claude Code skill
  pyproject.toml
  agentc/               # the CLI package
  .agentc/manifest.json # compiled-agent registry
  docs/plan.md          # implementation plan
  <agent-name>/         # one subdir per compiled agent
    skill/              # hard copy of the source skill (input only)
    claude-code/        # Claude Code adapter output
    agent.toml          # metadata: source_path, source_hash, harnesses
    README.md
    .env.example
```

## Status

v0. Claude Code adapter only. See `docs/plan.md`.
