"""Tool for running subagents via profiles or markdown definitions."""

from __future__ import annotations

from typing import Any

from agent_toolkit.subagents import SubagentRunner, SubagentTask, format_subagent_results
from agent_toolkit.tools.registry import registered_tool


@registered_tool(
    name="subagent",
    description=(
        "Run one or more subagents using configured profiles or markdown definitions. "
        "Supports chain (sequential) or parallel execution."
    ),
    category="agents",
    tags=("subagent", "orchestration"),
    input_schema={
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["chain", "parallel"],
                "description": "Execution mode for subagents.",
            },
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "agent": {"type": "string", "description": "Subagent name."},
                        "prompt": {"type": "string", "description": "Task prompt."},
                        "model": {"type": "string", "description": "Optional model override."},
                    },
                    "required": ["agent", "prompt"],
                },
            },
        },
        "required": ["tasks"],
    },
    output_schema={"type": "string"},
    capabilities=("delegate",),
    source="agent:subagent",
)
def subagent(tasks: list[dict[str, Any]], mode: str = "chain") -> str:
    """Run subagent tasks and return aggregated output."""
    if mode not in {"chain", "parallel"}:
        return "Invalid subagent mode. Use 'chain' or 'parallel'."

    task_list: list[SubagentTask] = []
    for task in tasks or []:
        agent = str(task.get("agent", "")).strip()
        prompt = str(task.get("prompt", "")).strip()
        model_override = str(task.get("model", "")).strip() or None
        if not agent or not prompt:
            continue
        task_list.append(SubagentTask(agent=agent, prompt=prompt, model_override=model_override))

    if not task_list:
        return "No valid subagent tasks provided."

    runner = SubagentRunner()
    results = runner.run_tasks(task_list, mode=mode)
    return format_subagent_results(results, mode)
