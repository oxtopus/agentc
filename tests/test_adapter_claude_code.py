from pathlib import Path

from agentc.adapters.claude_code import ClaudeCodeAdapter
from agentc.ingest import parse
from agentc.ir import CompileOpts

FIXTURES = Path(__file__).parent / "fixtures" / "skills"


def test_emit_run_sh(tmp_path):
    skill = parse(FIXTURES / "basic")
    opts = CompileOpts(name="basic", out_dir=tmp_path, harnesses=["claude-code"])
    ClaudeCodeAdapter().emit(skill, tmp_path, opts)
    run_sh = tmp_path / "claude-code" / "run.sh"
    assert run_sh.is_file()
    assert run_sh.stat().st_mode & 0o111
    body = run_sh.read_text()
    assert "exec claude" in body
    assert "--allowedTools 'Bash(echo *)'" in body


def test_emit_no_tools_omits_allowed_flag(tmp_path):
    skill = parse(FIXTURES / "conditional")
    opts = CompileOpts(name="conditional", out_dir=tmp_path, harnesses=["claude-code"])
    ClaudeCodeAdapter().emit(skill, tmp_path, opts)
    body = (tmp_path / "claude-code" / "run.sh").read_text()
    assert "--allowedTools" not in body
