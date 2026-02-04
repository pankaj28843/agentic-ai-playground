"""Tool catalog with capability-aware expansion."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from agent_toolkit.config.service import ConfigService, get_config_service
from agent_toolkit.config.tool_expansion import (
    expand_tools_and_capabilities,
    resolve_tool_groups,
)

if TYPE_CHECKING:
    from agent_toolkit.config.schema import ToolGroup
    from agent_toolkit.models.settings import Settings
    from agent_toolkit.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolSelection:
    """Resolved tool names and aggregated capabilities."""

    tools: list[str]
    capabilities: tuple[str, ...]
    tool_groups: tuple[str, ...] = ()


@dataclass(frozen=True)
class CapabilityPolicy:
    """Allow/deny policy for tool group capabilities."""

    allowlist: tuple[str, ...] = ()
    denylist: tuple[str, ...] = ()

    @classmethod
    def from_settings(cls, settings: Settings) -> CapabilityPolicy:
        """Create policy from runtime settings."""
        allowlist = tuple(settings.capability_allowlist)
        denylist = tuple(settings.capability_denylist)
        return cls(allowlist=allowlist, denylist=denylist)

    def enabled(self) -> bool:
        """Return True when any policy rule is defined."""
        return bool(self.allowlist or self.denylist)

    def allows(self, group_name: str, group: ToolGroup) -> bool:
        """Return True if a tool group is permitted by policy."""
        if not self.enabled():
            return True
        capabilities = set(group.capabilities)
        if self.denylist and any(cap in self.denylist for cap in capabilities):
            logger.info(
                "Capability policy denied tool group '%s' (capabilities=%s)",
                group_name,
                group.capabilities,
            )
            return False
        if self.allowlist and not capabilities.intersection(self.allowlist):
            if not capabilities:
                return True
            logger.info(
                "Capability policy skipped tool group '%s' (capabilities=%s)",
                group_name,
                group.capabilities,
            )
            return False
        return True


class ToolCatalog:
    """Resolve tools and tool groups from configuration and registry."""

    def __init__(
        self,
        registry: ToolRegistry,
        config_service: ConfigService | None = None,
        capability_policy: CapabilityPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._config_service = config_service or get_config_service()
        self._capability_policy = capability_policy or CapabilityPolicy.from_settings(
            self._config_service.get_settings()
        )
        if self._capability_policy.enabled():
            logger.info(
                "Capability policy enabled: allowlist=%s denylist=%s",
                self._capability_policy.allowlist,
                self._capability_policy.denylist,
            )

    def expand_tools(
        self,
        agent_name: str,
        tool_groups_override: list[str] | None = None,
    ) -> ToolSelection:
        """Expand tool groups and return tools plus capabilities."""
        schema = self._config_service.get_schema()
        resolved_groups = resolve_tool_groups(schema, agent_name, tool_groups_override)
        if self._capability_policy.enabled():
            resolved_groups = [
                (name, group)
                for name, group in resolved_groups
                if self._capability_policy.allows(name, group)
            ]
        tools, capabilities = expand_tools_and_capabilities(
            schema,
            agent_name,
            tool_groups_override,
            resolved_groups=resolved_groups,
        )
        selected_group_names = tuple(name for name, _ in resolved_groups)
        unique_tools = tools
        unique_capabilities = tuple(capabilities)
        return ToolSelection(
            tools=unique_tools,
            capabilities=unique_capabilities,
            tool_groups=selected_group_names,
        )

    def capability_policy_enabled(self) -> bool:
        """Return True if capability policy is active."""
        return self._capability_policy.enabled()

    def resolve_strands_tools(self, tool_names: list[str]) -> list[Any]:
        """Resolve tool callables for Strands execution."""
        return self._registry.to_strands_tools(tool_names)

    def registry(self) -> ToolRegistry:
        """Return the underlying tool registry."""
        return self._registry
