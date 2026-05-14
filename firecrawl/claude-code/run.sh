#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
export CLAUDE_HOME="$HERE/.claude"
export CLAUDE_CONFIG_DIR="$HERE/.claude"
exec claude "$@"
