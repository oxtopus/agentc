#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
AGENT_DIR="$(cd "$HERE/.." && pwd)"
cd "$AGENT_DIR"
if [ -f "$AGENT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$AGENT_DIR/.env"
  set +a
fi
exec claude \
  --bare \
  --append-system-prompt-file "$AGENT_DIR/skill/SKILL.md" \
  --add-dir "$AGENT_DIR/skill" \
  --allowedTools 'Bash(firecrawl *),Bash(npx firecrawl *)' \
  "$@"
