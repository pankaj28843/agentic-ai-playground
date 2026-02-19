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
    ) -> AgentProfile:
        """Return a profile copy with capability policy applied."""
        if not self.catalog.capability_policy_enabled():
            return profile

        selection = self.catalog.expand_tools(profile.name, None)
        return profile.model_copy(
            update={"tools": selection.tools, "tool_groups": list(selection.tool_groups)}
        )
