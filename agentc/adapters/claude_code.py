from __future__ import annotations

import json
import shutil
from pathlib import Path

from agentc.ir import CompileOpts, ParsedSkill


class ClaudeCodeAdapter:
    name = "claude-code"

    def emit(self, skill: ParsedSkill, agent_dir: Path, opts: CompileOpts) -> None:
        cc_dir = agent_dir / "claude-code"
        cc_dir.mkdir(parents=True, exist_ok=True)

        settings = {
            "model": opts.model,
            "permissions": {"allow": list(skill.allowed_tools)},
        }
        claude_dir = cc_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / "settings.json").write_text(
            json.dumps(settings, indent=2, sort_keys=True) + "\n"
        )

        skills_dst = claude_dir / "skills" / skill.name
        if skills_dst.exists():
            shutil.rmtree(skills_dst)
        skills_dst.mkdir(parents=True)
        (skills_dst / "SKILL.md").write_text((skill.source_dir / "SKILL.md").read_text())
        for sub in ("references", "rules"):
            src = skill.source_dir / sub
            if src.is_dir():
                shutil.copytree(src, skills_dst / sub)

        run_sh = cc_dir / "run.sh"
        run_sh.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            'HERE="$(cd "$(dirname "$0")" && pwd)"\n'
            'cd "$HERE"\n'
            'export CLAUDE_HOME="$HERE/.claude"\n'
            'export CLAUDE_CONFIG_DIR="$HERE/.claude"\n'
            'exec claude "$@"\n'
        )
        run_sh.chmod(0o755)

    def entrypoint(self, agent_dir: Path) -> Path:
        return agent_dir / "claude-code" / "run.sh"
