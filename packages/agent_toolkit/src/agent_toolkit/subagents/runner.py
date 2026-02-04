"""Subagent orchestration helpers."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import Iterable

from agent_toolkit.agents.factory import AgentFactory
from agent_toolkit.config import load_profiles, load_settings
from agent_toolkit.config.service import get_config_service
from agent_toolkit.mcp.client_resolver import get_mcp_clients_for_profile
from agent_toolkit.models.profiles import AgentProfile
from agent_toolkit.subagents.loader import SubagentLoader
from agent_toolkit.subagents.models import SubagentDefinition, SubagentResult, SubagentTask
from agent_toolkit.tools import DEFAULT_TOOL_REGISTRY, ToolRegistry

logger = logging.getLogger(__name__)


class SubagentRunner:
    """Run subagents sequentially or in parallel."""

    def __init__(
        self,
        *,
        settings=None,
        registry: ToolRegistry | None = None,
        profiles: dict[str, AgentProfile] | None = None,
        definitions: dict[str, SubagentDefinition] | None = None,
        tool_groups: dict[str, list[str]] | None = None,
        factory: AgentFactory | None = None,
        cwd: str | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._registry = registry or DEFAULT_TOOL_REGISTRY
        self._profiles = (
            profiles if profiles is not None else load_profiles(registry=self._registry)
        )
        self._tool_groups = tool_groups if tool_groups is not None else self._load_tool_groups()
        self._definitions = definitions if definitions is not None else self._load_definitions(cwd)
        self._factory = factory or AgentFactory(settings=self._settings, registry=self._registry)

    def run_tasks(self, tasks: Iterable[SubagentTask], mode: str = "chain") -> list[SubagentResult]:
        """Run the provided subagent tasks."""
        task_list = list(tasks)
        if not task_list:
            return []

        if mode == "parallel":
            return self._run_parallel(task_list)
        return self._run_chain(task_list)

    def _run_chain(self, tasks: list[SubagentTask]) -> list[SubagentResult]:
        results: list[SubagentResult] = []
        context = ""
        for task in tasks:
            prompt = task.prompt
            if context:
                prompt = f"{prompt}\n\nContext from previous agent:\n{context}"
            result = self._run_single(task, prompt)
            results.append(result)
            if result.output:
                context = result.output
        return results

    def _run_parallel(self, tasks: list[SubagentTask]) -> list[SubagentResult]:
        with ThreadPoolExecutor(max_workers=min(len(tasks), 4)) as executor:
            future_map = {
                executor.submit(self._run_single, task, task.prompt): task for task in tasks
            }
            return [future.result() for future in as_completed(future_map)]

    def _run_single(self, task: SubagentTask, prompt: str) -> SubagentResult:
        profile = self._resolve_profile(task)
        if profile is None:
            return SubagentResult(
                agent=task.agent,
                prompt=prompt,
                output="",
                error=f"Unknown subagent: {task.agent}",
            )

        try:
            mcp_clients = get_mcp_clients_for_profile(profile)
            agent = self._factory.create_from_profile(
                profile,
                session_id=f"subagent-{profile.name}-{uuid4()}",
                mcp_clients=mcp_clients if mcp_clients else None,
            )
            result = agent(prompt)
            output = (
                getattr(result, "output", None) or getattr(result, "message", None) or str(result)
            )
            return SubagentResult(agent=task.agent, prompt=prompt, output=str(output))
        except Exception as exc:
            logger.exception("Subagent '%s' failed", task.agent)
            return SubagentResult(agent=task.agent, prompt=prompt, output="", error=str(exc))

    def _resolve_profile(self, task: SubagentTask) -> AgentProfile | None:
        profile = self._profiles.get(task.agent)
        if profile is None:
            definition = self._definitions.get(task.agent)
            if definition is None:
                return None
            profile = self._build_profile_from_definition(definition)

        if task.model_override:
            profile = profile.model_copy(update={"model": task.model_override})
        return profile

    def _build_profile_from_definition(self, definition: SubagentDefinition) -> AgentProfile:
        tools = list(definition.tools)
        for group in definition.tool_groups:
            tools.extend(self._tool_groups.get(group, []))
        tools = _dedupe(tools)
        return AgentProfile(
            name=definition.name,
            description=definition.description,
            model=definition.model,
            system_prompt=definition.system_prompt,
            tools=tools,
            tool_groups=list(definition.tool_groups),
            extends="",
            metadata={"source": definition.source},
            constraints={},
        )

    def _load_tool_groups(self) -> dict[str, list[str]]:
        schema = get_config_service().get_schema()
        return {name: list(group.tools) for name, group in schema.tool_groups.items()}

    def _load_definitions(self, cwd: str | None) -> dict[str, SubagentDefinition]:
        loader = SubagentLoader(cwd or ".", self._settings.playground_config_dir)
        return loader.load().definitions


def format_subagent_results(results: list[SubagentResult], mode: str) -> str:
    """Format subagent results for display in a response."""
    if not results:
        return "No subagent tasks provided."

    lines = [f"Subagent results (mode={mode}):"]
    for idx, result in enumerate(results, start=1):
        label = f"{idx}. {result.agent}"
        if result.error:
            lines.append(f"{label} (error): {result.error}")
            continue
        lines.append(label)
        lines.append(result.output)
    return "\n".join(lines)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique
