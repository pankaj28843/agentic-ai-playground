from dataclasses import dataclass
from typing import Any

from agent_toolkit.hooks import ToolApprovalHook


@dataclass
class FakeEvent:
    tool_use: dict[str, Any]
    cancel_tool: str | None = None

    def interrupt(self, _name: str, reason: dict[str, Any]) -> str:
        _ = reason
        return "n"


def test_tool_approval_hook_blocks() -> None:
    hook = ToolApprovalHook(["root_search"], namespace="test")
    event = FakeEvent(tool_use={"name": "root_search", "input": {}})
    hook.approve(event)
    assert event.cancel_tool
