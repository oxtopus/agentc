---
name: agentc
description: |
  Compile an agent skill into a standalone, runnable agent project. Use when the user says "compile this skill", "make a standalone harness for <skill>", "wrap <skill> as a runnable agent", "package this skill", or "build an agent from <skill>". Also use when the user wants to inspect a parsed skill IR ("validate skill", "show IR"). Do NOT use for authoring new skills — only for wrapping existing ones.
allowed-tools:
  - Bash(agentc *)
  - Bash(python -m agentc *)
---

# agentc

Compile a skill (SKILL.md + optional `references/` and `rules/`) into a self-contained, runnable agent project. The compiled agent lives as a sibling subdirectory of `/home/austin/agentc/` and runs against an isolated Claude Code environment by default.

## Commands

- `agentc validate <skill-path>` — parse a skill, print the IR. No writes.
- `agentc compile <skill-path>` — emit a compiled agent (Claude Code by default).
- `agentc list` — list compiled agents.
- `agentc run <name>` — run a compiled agent.
- `agentc update <name>` — re-compile from the source skill, preserving `.env`.
- `agentc remove <name>` — delete a compiled agent.

Run `agentc --help` for full flags.

## Quickstart

```bash
agentc compile /home/austin/.agents/skills/firecrawl
agentc run firecrawl
```

This emits `/home/austin/agentc/firecrawl/` with `skill/`, `claude-code/`, `agent.toml`, and a `run.sh`. The compiled agent uses an isolated `CLAUDE_HOME` so it does not inherit global Claude Code settings or hooks.

## Choosing a harness

Default is Claude Code. Other adapters (OpenCode, Codex, raw API) ship later behind `--harness`.

| Harness     | Flag                   | Status   |
| ----------- | ---------------------- | -------- |
| Claude Code | `--harness claude-code` | default |
| OpenCode    | `--harness opencode`    | planned |
| Codex       | `--harness codex`       | planned |
| Raw API     | `--harness raw-api`     | planned |

## Re-compiling

`agentc update <name>` re-parses the source skill and overwrites generated files. `.env` and any `[user_overrides]` block in `agent.toml` are preserved.

## Notes

- The source skill is **input only**. The compiled agent owns its own hard copy under `skill/`. Edits to the source skill require `agentc update` to propagate.
- Cross-skill references (`../sibling/SKILL.md`) are recorded in `agent.toml` but not bundled. Compile each skill separately if you need multiple.
