"""Plan mode enforcement hook."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry

if TYPE_CHECKING:
    from agent_toolkit.plan_mode import PlanModeSettings


class PlanModeHook(HookProvider):
    """Restrict tool usage when plan mode is enabled."""

    def __init__(
        self,
        settings: PlanModeSettings,
        shell_tool_names: Iterable[str] = ("shell",),
    ) -> None:
        self._settings = settings
        self._shell_tool_names = {name.strip() for name in shell_tool_names if str(name).strip()}

    def register_hooks(self, registry: HookRegistry, **_kwargs: Any) -> None:
        """Register plan mode enforcement hooks."""
        registry.add_callback(BeforeToolCallEvent, self._enforce)

    def enforce(self, event: BeforeToolCallEvent) -> None:
        """Apply plan mode enforcement to a tool call event."""
        self._enforce(event)

    def _enforce(self, event: BeforeToolCallEvent) -> None:
        if not self._settings.enabled:
            return
        tool_name = event.tool_use.get("name")
        if tool_name not in self._shell_tool_names:
            return

        commands = _extract_shell_commands(event.tool_use.get("input"))
        if not commands:
            event.cancel_tool = "Shell command blocked in plan mode."
            return

        blocked = [cmd for cmd in commands if not _is_allowed(cmd, self._settings.shell_allowlist)]
        if blocked:
            event.cancel_tool = f"Shell command blocked in plan mode: {blocked[0]}"


def _extract_shell_commands(payload: Any) -> list[str]:
    command = payload.get("command") if isinstance(payload, dict) else payload

    if isinstance(command, str):
        return [command]

    if isinstance(command, list):
        commands: list[str] = []
        for item in command:
            if isinstance(item, str):
                commands.append(item)
            elif isinstance(item, dict):
                value = item.get("command")
                if isinstance(value, str):
                    commands.append(value)
        return commands

    return []


def _is_allowed(command: str, allowlist: tuple[str, ...]) -> bool:
    candidate = command.strip()
    if not candidate or not allowlist:
        return False
    return any(candidate == prefix or candidate.startswith(f"{prefix} ") for prefix in allowlist)
