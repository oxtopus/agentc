from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
import tomli_w
import typer

from agentc import __version__
from agentc.adapters import ADAPTERS
from agentc.ingest import parse
from agentc.ir import CompileOpts, ParsedSkill
from agentc import registry, util

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Compile an agent skill into a standalone, runnable agent project.",
)

_AGENT_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _repo_root() -> Path:
    env = os.environ.get("AGENTC_REPO")
    if env:
        return Path(env).resolve()
    cur = Path.cwd().resolve()
    for parent in [cur, *cur.parents]:
        if (parent / ".agentc" / "manifest.json").is_file():
            return parent
    return Path.home() / ".agentc-repo"


def _validate_agent_name(name: str) -> str:
    if not isinstance(name, str) or not name:
        raise typer.BadParameter("agent name must be a non-empty string")
    if not _AGENT_NAME_RE.match(name):
        raise typer.BadParameter(
            f"invalid agent name {name!r}: must match {_AGENT_NAME_RE.pattern}"
        )
    return name


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _agent_dir(repo: Path, name: str) -> Path:
    _validate_agent_name(name)
    repo_resolved = repo.resolve()
    candidate = (repo_resolved / name).resolve()
    if not _is_relative_to(candidate, repo_resolved) or candidate == repo_resolved:
        raise typer.BadParameter(
            f"agent path {candidate} escapes repo {repo_resolved}"
        )
    return candidate


def _write_agent_toml(
    agent_dir: Path,
    *,
    name: str,
    skill: ParsedSkill,
    source_hash: str,
    harnesses: list[str],
) -> None:
    toml_path = agent_dir / "agent.toml"
    user_overrides: dict = {}
    if toml_path.is_file():
        existing = tomllib.loads(toml_path.read_text())
        user_overrides = existing.get("user_overrides", {})
    doc = {
        "name": name,
        "source_path": str(skill.source_dir),
        "source_hash": source_hash,
        "agentc_version": __version__,
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "harnesses": harnesses,
        "sibling_refs": list(skill.sibling_refs),
        "user_overrides": user_overrides,
    }
    toml_path.write_text(tomli_w.dumps(doc))


def _write_shared(agent_dir: Path, skill: ParsedSkill, harnesses: list[str]) -> None:
    skill_dst = agent_dir / "skill"
    if skill_dst.exists():
        shutil.rmtree(skill_dst)
    util.copy_tracked_tree(skill.source_dir, skill_dst)

    env_example = agent_dir / ".env.example"
    if not env_example.is_file():
        env_example.write_text(
            "ANTHROPIC_API_KEY=\n"
            "# Optional: pin a specific model. Format depends on auth backend.\n"
            "# ANTHROPIC_MODEL=\n"
            "# If using Bedrock instead of the Anthropic API:\n"
            "# CLAUDE_CODE_USE_BEDROCK=1\n"
            "# AWS_PROFILE=\n"
            "# AWS_REGION=\n"
        )

    gitignore = agent_dir / ".gitignore"
    if not gitignore.is_file():
        gitignore.write_text(".env\n.venv/\n__pycache__/\n")

    run_targets = "\n".join(f"- `{h}/run.sh`" for h in harnesses)
    readme = agent_dir / "README.md"
    readme.write_text(
        f"# {skill.name}\n\n"
        f"{skill.description}\n\n"
        "## Run\n\n"
        f"{run_targets}\n\n"
        "## Source\n\n"
        f"Compiled from `{skill.source_dir}` via `agentc`. "
        "Use `agentc update` to re-compile after the source skill changes.\n"
    )


def _compile(skill_path: Path, *, name: str | None, harnesses: list[str], force: bool) -> Path:
    skill = parse(skill_path)
    agent_name = util.slugify(name or skill.name)
    repo = _repo_root()
    agent_dir = _agent_dir(repo, agent_name)

    deduped: list[str] = []
    seen: set[str] = set()
    for h in harnesses:
        if h in seen:
            continue
        seen.add(h)
        deduped.append(h)
    harnesses = deduped

    unknown = [h for h in harnesses if h not in ADAPTERS]
    if unknown:
        raise typer.BadParameter(
            f"unknown harness(es): {', '.join(unknown)}. Known: {sorted(ADAPTERS)}"
        )

    if agent_dir.exists() and not force:
        existing_marker = agent_dir / "agent.toml"
        if not existing_marker.is_file():
            raise typer.BadParameter(
                f"{agent_dir} exists and is not an agentc-managed directory; refusing to overwrite."
            )

    agent_dir.mkdir(parents=True, exist_ok=True)
    _write_shared(agent_dir, skill, harnesses)

    opts = CompileOpts(name=agent_name, out_dir=agent_dir, harnesses=harnesses, force=force)
    for h in harnesses:
        ADAPTERS[h]().emit(skill, agent_dir, opts)

    source_hash = util.hash_dir(skill.source_dir)
    _write_agent_toml(
        agent_dir, name=agent_name, skill=skill, source_hash=source_hash, harnesses=harnesses
    )
    registry.upsert(
        repo,
        name=agent_name,
        source_path=skill.source_dir,
        source_hash=source_hash,
        harnesses=harnesses,
    )
    if skill.sibling_refs:
        typer.echo(
            f"  warning: source skill references {len(skill.sibling_refs)} sibling skill(s) "
            f"not bundled: {', '.join(skill.sibling_refs)}",
            err=True,
        )
    return agent_dir


@app.command()
def validate(skill_path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True)) -> None:
    """Parse a skill and print its IR. No writes."""
    skill = parse(skill_path)
    out = {
        "name": skill.name,
        "description": skill.description[:120] + ("…" if len(skill.description) > 120 else ""),
        "allowed_tools": skill.allowed_tools,
        "source_dir": str(skill.source_dir),
        "section_count": len(skill.sections),
        "conditional_sections": sum(1 for s in skill.sections if s.conditional),
        "reference_files": len(skill.references),
        "rule_files": len(skill.rules),
        "sibling_refs": skill.sibling_refs,
    }
    typer.echo(json.dumps(out, indent=2))


@app.command()
def compile(
    skill_path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    harness: list[str] = typer.Option(
        ["claude-code"],
        "--harness",
        "-h",
        help="Harness to emit (repeatable). Default: claude-code.",
    ),
    name: str = typer.Option(None, "--name", help="Compiled agent name (default: skill name)."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing compiled agent."),
) -> None:
    """Compile a skill into a standalone agent project."""
    agent_dir = _compile(skill_path, name=name, harnesses=list(harness), force=force)
    typer.echo(f"compiled: {agent_dir}")


@app.command(name="list")
def list_cmd() -> None:
    """List compiled agents."""
    data = registry.load(_repo_root())
    agents = data.get("agents", [])
    if not agents:
        typer.echo(f"(no compiled agents under {_repo_root()})")
        return
    width = max(len(a["name"]) for a in agents)
    for a in agents:
        harnesses = ",".join(a.get("harnesses", []))
        typer.echo(f"{a['name']:<{width}}  {harnesses}  {a.get('source_path', '')}")


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def run(
    ctx: typer.Context,
    name: str,
    harness: str | None = typer.Option(None, "--harness", "-h"),
) -> None:
    """Run a compiled agent via its harness entrypoint.

    Extra positional args become a one-shot prompt (non-interactive).
    Pass flags after `--` to forward them verbatim to the underlying tool.
    """
    repo = _repo_root()
    entry_meta = registry.find(repo, name)
    if not entry_meta:
        typer.echo(f"unknown agent: {name}", err=True)
        raise typer.Exit(code=1)
    if harness is None:
        harness = (entry_meta.get("harnesses") or ["claude-code"])[0]
    cls = ADAPTERS.get(harness)
    if cls is None:
        typer.echo(f"unknown harness: {harness}", err=True)
        raise typer.Exit(code=1)
    entry = cls().entrypoint(_agent_dir(repo, name))
    if not entry.is_file():
        typer.echo(f"missing entrypoint: {entry}", err=True)
        raise typer.Exit(code=1)

    extras = list(ctx.args)
    forward: list[str]
    if extras and all(not a.startswith("-") for a in extras):
        forward = ["-p", " ".join(extras)]
    else:
        forward = extras
    os.execvp(str(entry), [str(entry), *forward])


@app.command()
def update(name: str) -> None:
    """Re-compile an agent from its recorded source skill."""
    repo = _repo_root()
    entry = registry.find(repo, name)
    if not entry:
        typer.echo(f"unknown agent: {name}", err=True)
        raise typer.Exit(code=1)
    skill_path = Path(entry["source_path"])
    if not skill_path.is_dir():
        typer.echo(f"source skill missing: {skill_path}", err=True)
        raise typer.Exit(code=1)
    agent_dir = _compile(
        skill_path,
        name=name,
        harnesses=entry.get("harnesses", ["claude-code"]),
        force=True,
    )
    typer.echo(f"updated: {agent_dir}")


@app.command()
def remove(name: str, force: bool = typer.Option(False, "--force")) -> None:
    """Delete a compiled agent and remove it from the manifest."""
    repo = _repo_root()
    if not registry.find(repo, name):
        typer.echo(f"unknown agent: {name}", err=True)
        raise typer.Exit(code=1)
    try:
        agent_dir = _agent_dir(repo, name)
    except typer.BadParameter as e:
        typer.echo(f"refusing to remove {name!r}: {e}", err=True)
        registry.remove(repo, name)
        raise typer.Exit(code=1)
    if not force:
        typer.confirm(f"Delete {agent_dir}?", abort=True)
    if agent_dir.exists():
        if not (agent_dir / "agent.toml").is_file():
            typer.echo(
                f"refusing to remove {agent_dir}: not an agentc-managed directory "
                "(no agent.toml)",
                err=True,
            )
            raise typer.Exit(code=1)
        shutil.rmtree(agent_dir)
    registry.remove(repo, name)
    typer.echo(f"removed: {name}")


@app.command()
def version() -> None:
    """Print the agentc version."""
    typer.echo(__version__)


if __name__ == "__main__":
    app()
