"""Strands tools adapter for integrating strands-agents-tools.

This module provides a bridge between strands_tools package and the agent_toolkit's
tool registry system, enabling declarative tool configuration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# Map of strands_tools names to their import paths
STRANDS_TOOLS_CATALOG = {
    # Basic utilities
    "current_time": "strands_tools.current_time:current_time",
    "calculator": "strands_tools.calculator:calculator",
    "sleep": "strands_tools.sleep:sleep",
    "think": "strands_tools.think:think",
    # File operations
    "file_read": "strands_tools.file_read:file_read",
    "file_write": "strands_tools.file_write:file_write",
    "editor": "strands_tools.editor:editor",
    # Shell/System
    "shell": "strands_tools.shell:shell",
    "environment": "strands_tools.environment:environment",
    # HTTP/Network
    "http_request": "strands_tools.http_request:http_request",
    # Search/Research
    "tavily": "strands_tools.tavily:tavily_search",
    "exa": "strands_tools.exa:exa_search",
    "rss": "strands_tools.rss:rss_read",
    # Memory/State
    "memory": "strands_tools.memory:memory",
    "journal": "strands_tools.journal:journal",
    # Agents/Coordination
    "use_agent": "strands_tools.use_agent:use_agent",
    "use_llm": "strands_tools.use_llm:use_llm",
    "handoff_to_user": "strands_tools.handoff_to_user:handoff_to_user",
    "stop": "strands_tools.stop:stop",
    # Code execution
    "python_repl": "strands_tools.python_repl:python_repl",
    # Image/Media
    "image_reader": "strands_tools.image_reader:image_reader",
    "generate_image": "strands_tools.generate_image:generate_image",
    "generate_image_stability": "strands_tools.generate_image_stability:generate_image_stability",
    # MCP
    "mcp_client": "strands_tools.mcp_client:mcp_client",
    # Diagram
    "diagram": "strands_tools.diagram:diagram",
    # AWS
    "use_aws": "strands_tools.use_aws:use_aws",
    # Workflow
    "workflow": "strands_tools.workflow:workflow",
    "cron": "strands_tools.cron:cron",
}

# Tool groups that bundle related tools
STRANDS_TOOL_GROUPS = {
    "basic": ["current_time", "calculator", "sleep", "think"],
    "files": ["file_read", "file_write", "editor"],
    "shell": ["shell", "environment"],
    "web": ["http_request", "tavily", "exa", "rss"],
    "memory": ["memory", "journal"],
    "agents": ["use_agent", "use_llm", "handoff_to_user", "stop"],
    "code": ["python_repl", "shell"],
    "media": ["image_reader", "generate_image", "generate_image_stability"],
}


def import_strands_tool(tool_name: str) -> Callable[..., Any] | None:
    """Import a strands tool by name.

    Args:
        tool_name: Name of the tool (e.g., "file_read", "current_time")

    Returns:
        The tool function, or None if not found/import failed
    """
    import_path = STRANDS_TOOLS_CATALOG.get(tool_name)
    if not import_path:
        logger.warning("Unknown strands tool: %s", tool_name)
        return None

    try:
        module_path, func_name = import_path.rsplit(":", 1)
        module = __import__(module_path, fromlist=[func_name])
        return getattr(module, func_name)
    except ImportError as e:
        logger.warning("Failed to import strands tool '%s': %s", tool_name, e)
        return None
    except AttributeError as e:
        logger.warning("Tool '%s' not found in module: %s", tool_name, e)
        return None


def get_strands_tools(tool_names: list[str]) -> list[Callable[..., Any]]:
    """Get a list of strands tools by name.

    Args:
        tool_names: List of tool names to import

    Returns:
        List of successfully imported tool functions
    """
    tools = []
    for name in tool_names:
        tool = import_strands_tool(name)
        if tool:
            tools.append(tool)
    return tools


def get_strands_tool_group(group_name: str) -> list[Callable[..., Any]]:
    """Get all tools in a strands tool group.

    Args:
        group_name: Name of the tool group (e.g., "files", "basic")

    Returns:
        List of tool functions in the group
    """
    tool_names = STRANDS_TOOL_GROUPS.get(group_name, [])
    if not tool_names:
        logger.warning("Unknown strands tool group: %s", group_name)
        return []
    return get_strands_tools(tool_names)


def list_available_tools() -> list[str]:
    """List all available strands tools."""
    return list(STRANDS_TOOLS_CATALOG.keys())


def list_tool_groups() -> dict[str, list[str]]:
    """List all tool groups and their tools."""
    return dict(STRANDS_TOOL_GROUPS)
