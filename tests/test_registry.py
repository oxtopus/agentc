from pathlib import Path

from agentc import registry


def _upsert(repo_root: Path, name: str) -> None:
    registry.upsert(
        repo_root,
        name=name,
        source_path=repo_root / "skills" / name,
        source_hash=f"sha256:{name}",
        harnesses=["claude-code"],
    )


def test_upsert_then_find(tmp_path):
    _upsert(tmp_path, "alpha")
    entry = registry.find(tmp_path, "alpha")
    assert entry is not None
    assert entry["name"] == "alpha"
    assert entry["harnesses"] == ["claude-code"]


def test_upsert_overwrites(tmp_path):
    _upsert(tmp_path, "alpha")
    _upsert(tmp_path, "alpha")
    data = registry.load(tmp_path)
    assert len([a for a in data["agents"] if a["name"] == "alpha"]) == 1


def test_remove_returns_true_for_existing(tmp_path):
    _upsert(tmp_path, "alpha")
    assert registry.remove(tmp_path, "alpha") is True
    assert registry.find(tmp_path, "alpha") is None


def test_remove_returns_false_for_missing(tmp_path):
    assert registry.remove(tmp_path, "ghost") is False
