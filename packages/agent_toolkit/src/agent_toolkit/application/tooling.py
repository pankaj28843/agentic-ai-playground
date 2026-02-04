"""Tooling helpers for execution pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_toolkit.models.profiles import AgentProfile
    from agent_toolkit.models.settings import Settings
    from agent_toolkit.tools.catalog import ToolCatalog


@dataclass(frozen=True)
class ToolingBuilder:
    """Apply tool/model overrides and resolve tool groups."""

    settings: Settings
    catalog: ToolCatalog

    def apply_profile_overrides(
        self,
        profile: AgentProfile,
        *,
        model_override: str | None,
        tool_groups_override: list[str] | None,
    ) -> AgentProfile:
        """Return a profile copy with overrides applied."""
        if (
            not model_override
            and tool_groups_override is None
            and not self.catalog.capability_policy_enabled()
        ):
            return profile

        updates: dict[str, object] = {}
        if model_override:
            updates["model"] = model_override

        if tool_groups_override is not None or self.catalog.capability_policy_enabled():
            selection = self.catalog.expand_tools(profile.name, tool_groups_override)
            updates["tools"] = selection.tools
            updates["tool_groups"] = list(selection.tool_groups)

        return profile.model_copy(update=updates)
