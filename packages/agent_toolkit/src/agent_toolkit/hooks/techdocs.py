"""TechDocs workflow enforcement hook.

Enforces the TechDocs tool workflow: find_tenant → root_search → root_fetch.
Prevents agents from calling root_fetch with arbitrary URLs.
"""

from __future__ import annotations

import logging
from typing import Any

from strands.hooks import (
    AfterToolCallEvent,
    BeforeInvocationEvent,
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)

logger = logging.getLogger(__name__)


class TechDocsWorkflowHook(HookProvider):
    """Enforce TechDocs tool workflow: find_tenant → root_search → root_fetch.

    Prevents agent from calling root_fetch with arbitrary URLs.
    URLs must come from root_search results to be valid.
    """

    def __init__(self) -> None:
        """Initialize workflow state tracking."""
        self._valid_urls: set[str] = set()
        self._known_tenants: set[str] = set()
        self._search_count: int = 0
        self._fetch_count: int = 0
        self._blocked_count: int = 0

    def register_hooks(self, registry: HookRegistry, **_kwargs: Any) -> None:
        """Register hooks for workflow enforcement."""
        registry.add_callback(BeforeInvocationEvent, self._reset_state)
        registry.add_callback(BeforeToolCallEvent, self._enforce_workflow)
        registry.add_callback(AfterToolCallEvent, self._capture_urls)

    def _reset_state(self, _event: BeforeInvocationEvent) -> None:
        """Reset state at start of each invocation."""
        self._valid_urls.clear()
        self._known_tenants.clear()
        self._search_count = 0
        self._fetch_count = 0
        self._blocked_count = 0

    def _enforce_workflow(self, event: BeforeToolCallEvent) -> None:
        """Block root_fetch calls with URLs not from search results."""
        tool_name = event.tool_use.get("name", "")
        tool_input = event.tool_use.get("input", {})

        if tool_name == "TechDocs-root_fetch":
            uri = tool_input.get("uri", "")

            # Block if no searches have been done yet
            if self._search_count == 0:
                event.cancel_tool = (
                    "WORKFLOW ERROR: You must call root_search first to get valid URLs. "
                    "The TechDocs workflow is: find_tenant → root_search → root_fetch. "
                    "Call root_search with your query to get URLs, then fetch those URLs."
                )
                self._blocked_count += 1
                logger.warning("Blocked root_fetch - no search done yet: %s", uri[:100])
                return

            # Block if URL is not from search results
            if uri and uri not in self._valid_urls:
                event.cancel_tool = (
                    f"WORKFLOW ERROR: URL '{uri[:80]}...' was not returned by root_search. "
                    "Only fetch URLs that appeared in search results. "
                    "If you need different content, run a new root_search query first."
                )
                self._blocked_count += 1
                logger.warning("Blocked root_fetch - URL not from search: %s", uri[:100])
                return

            self._fetch_count += 1

        elif tool_name == "TechDocs-root_search":
            self._search_count += 1

    def _capture_urls(self, event: AfterToolCallEvent) -> None:
        """Extract URLs from search results to build valid URL set."""
        tool_name = event.tool_use.get("name", "")

        if tool_name == "TechDocs-root_search":
            result = event.tool_result
            if isinstance(result, dict):
                results = result.get("results", [])
                for item in results:
                    if isinstance(item, dict) and "url" in item:
                        self._valid_urls.add(item["url"])
                logger.debug(
                    "Captured %d URLs from search, total valid: %d",
                    len(results),
                    len(self._valid_urls),
                )

        elif tool_name == "TechDocs-find_tenant":
            result = event.tool_result
            if isinstance(result, dict):
                tenants = result.get("tenants", [])
                for tenant in tenants:
                    if isinstance(tenant, dict) and "codename" in tenant:
                        self._known_tenants.add(tenant["codename"])
