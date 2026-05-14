from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

MANIFEST = ".agentc/manifest.json"


def _manifest_path(repo_root: Path) -> Path:
    return repo_root / MANIFEST


def load(repo_root: Path) -> dict:
    p = _manifest_path(repo_root)
    if not p.is_file():
        return {"agents": []}
    return json.loads(p.read_text())


def save(repo_root: Path, data: dict) -> None:
    p = _manifest_path(repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def upsert(
    repo_root: Path,
    *,
    name: str,
    source_path: Path,
    source_hash: str,
    harnesses: list[str],
) -> None:
    data = load(repo_root)
    entry = {
        "name": name,
        "source_path": str(source_path),
        "source_hash": source_hash,
        "harnesses": harnesses,
        "compiled_at": datetime.now(timezone.utc).isoformat(),
    }
    agents = [a for a in data.get("agents", []) if a.get("name") != name]
    agents.append(entry)
    agents.sort(key=lambda a: a["name"])
    data["agents"] = agents
    save(repo_root, data)


def remove(repo_root: Path, name: str) -> bool:
    data = load(repo_root)
    before = len(data.get("agents", []))
    data["agents"] = [a for a in data.get("agents", []) if a.get("name") != name]
    save(repo_root, data)
    return len(data["agents"]) != before


def find(repo_root: Path, name: str) -> dict | None:
    for a in load(repo_root).get("agents", []):
        if a.get("name") == name:
            return a
    return None
