from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from agentc.ir import CompileOpts, ParsedSkill


class HarnessAdapter(ABC):
    name: str

    @abstractmethod
    def emit(self, skill: ParsedSkill, agent_dir: Path, opts: CompileOpts) -> None:
        ...

    @abstractmethod
    def entrypoint(self, agent_dir: Path) -> Path:
        """Path to the executable that runs the compiled agent."""


from agentc.adapters.claude_code import ClaudeCodeAdapter  # noqa: E402

ADAPTERS: dict[str, type[HarnessAdapter]] = {
    ClaudeCodeAdapter.name: ClaudeCodeAdapter,
}
