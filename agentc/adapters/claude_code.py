from __future__ import annotations

import shlex
from pathlib import Path

from agentc.ir import CompileOpts, ParsedSkill


class ClaudeCodeAdapter:
    name = "claude-code"

    def emit(self, skill: ParsedSkill, agent_dir: Path, opts: CompileOpts) -> None:
        cc_dir = agent_dir / "claude-code"
        cc_dir.mkdir(parents=True, exist_ok=True)

        allowed_arg = ",".join(skill.allowed_tools)
        allowed_line = (
            f"  --allowedTools {shlex.quote(allowed_arg)} \\\n"
            if skill.allowed_tools
            else ""
        )

        run_sh = cc_dir / "run.sh"
        run_sh.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            'HERE="$(cd "$(dirname "$0")" && pwd)"\n'
            'AGENT_DIR="$(cd "$HERE/.." && pwd)"\n'
            'cd "$AGENT_DIR"\n'
            'if [ -f "$AGENT_DIR/.env" ]; then\n'
            '  set -a\n'
            '  # shellcheck disable=SC1091\n'
            '  . "$AGENT_DIR/.env"\n'
            '  set +a\n'
            'fi\n'
            'exec claude \\\n'
            '  --bare \\\n'
            '  --append-system-prompt-file "$AGENT_DIR/skill/SKILL.md" \\\n'
            '  --add-dir "$AGENT_DIR/skill" \\\n'
            f'{allowed_line}'
            '  "$@"\n'
        )
        run_sh.chmod(0o755)

    def entrypoint(self, agent_dir: Path) -> Path:
        return agent_dir / "claude-code" / "run.sh"
