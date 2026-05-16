from __future__ import annotations

import hashlib
import re
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".mypy_cache", ".pytest_cache"}
SKIP_FILES = {".DS_Store"}


def is_tracked_file(p: Path) -> bool:
    if any(part in SKIP_DIRS for part in p.parts):
        return False
    return p.is_file() and p.name not in SKIP_FILES


def iter_tracked_files(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return sorted(p for p in path.rglob("*") if is_tracked_file(p))


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return s or "agent"


def hash_dir(path: Path) -> str:
    h = hashlib.sha256()
    for f in iter_tracked_files(path):
        h.update(str(f.relative_to(path)).encode())
        h.update(b"\0")
        h.update(f.read_bytes())
        h.update(b"\0")
    return "sha256:" + h.hexdigest()
