from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from agentc import cli, registry

FIXTURES = Path(__file__).parent / "fixtures" / "skills"


def test_validate_agent_name_accepts_slug():
    assert cli._validate_agent_name("foo-bar-1") == "foo-bar-1"


@pytest.mark.parametrize(
    "name",
    ["", ".", "..", "../victim", "foo/bar", "foo\\bar", "Foo", "-foo", "foo--bar", "/abs"],
)
def test_validate_agent_name_rejects_bad(name):
    with pytest.raises(typer.BadParameter):
        cli._validate_agent_name(name)


def test_agent_dir_resolves_under_repo(tmp_path):
    d = cli._agent_dir(tmp_path, "foo")
    assert d == (tmp_path.resolve() / "foo")


def test_agent_dir_rejects_traversal(tmp_path):
    with pytest.raises(typer.BadParameter):
        cli._agent_dir(tmp_path, "../victim")


def test_remove_bad_name_leaves_sibling_intact(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "important.txt").write_text("keep")

    manifest = {
        "agents": [
            {
                "name": "../victim",
                "source_path": str(tmp_path / "src"),
                "source_hash": "sha256:x",
                "harnesses": ["claude-code"],
            }
        ]
    }
    import json as _json

    (repo / ".agentc").mkdir()
    (repo / ".agentc" / "manifest.json").write_text(_json.dumps(manifest))

    monkeypatch.setenv("AGENTC_REPO", str(repo))

    runner = CliRunner()
    result = runner.invoke(cli.app, ["remove", "../victim", "--force"])
    assert result.exit_code != 0
    assert victim.is_dir()
    assert (victim / "important.txt").read_text() == "keep"
    # malformed entry should have been stripped from manifest
    assert registry.find(repo, "../victim") is None


def test_remove_refuses_unmanaged_dir(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".agentc").mkdir()
    target = repo / "demo"
    target.mkdir()
    (target / "important.txt").write_text("keep")

    import json as _json

    (repo / ".agentc" / "manifest.json").write_text(
        _json.dumps(
            {
                "agents": [
                    {
                        "name": "demo",
                        "source_path": str(tmp_path / "src"),
                        "source_hash": "sha256:x",
                        "harnesses": ["claude-code"],
                    }
                ]
            }
        )
    )

    monkeypatch.setenv("AGENTC_REPO", str(repo))
    runner = CliRunner()
    result = runner.invoke(cli.app, ["remove", "demo", "--force"])
    assert result.exit_code != 0
    assert (target / "important.txt").is_file()


def test_compile_rejects_unknown_harness_before_writes(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("AGENTC_REPO", str(repo))

    with pytest.raises(typer.BadParameter):
        cli._compile(FIXTURES / "basic", name=None, harnesses=["nope"], force=False)

    assert not (repo / "basic").exists()


def test_compile_dedupes_harnesses(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("AGENTC_REPO", str(repo))

    cli._compile(
        FIXTURES / "basic",
        name=None,
        harnesses=["claude-code", "claude-code"],
        force=False,
    )
    entry = registry.find(repo, "basic")
    assert entry is not None
    assert entry["harnesses"] == ["claude-code"]

    import sys as _sys

    if _sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
    doc = tomllib.loads((repo / "basic" / "agent.toml").read_text())
    assert doc["harnesses"] == ["claude-code"]


def test_compile_persists_sibling_refs(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("AGENTC_REPO", str(repo))

    cli._compile(
        FIXTURES / "with-refs",
        name=None,
        harnesses=["claude-code"],
        force=False,
    )

    import sys as _sys

    if _sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
    doc = tomllib.loads((repo / "with-refs" / "agent.toml").read_text())
    assert doc["sibling_refs"] == ["other"]

    captured = capsys.readouterr()
    assert "sibling skill" in captured.err
