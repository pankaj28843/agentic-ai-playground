"""Tools package for agent toolkit.

This package provides:
- ToolRegistry: Central registry for tool definitions and handlers
- @registered_tool: Decorator for registering Strands tools with metadata
- MCPPromptClient/MCPResourceClient: Clients for MCP prompts and resources
- strands_tools adapter: Import and use tools from strands-agents-tools

The registry enables configuration-driven tool composition where profiles
reference tools by name rather than importing callables directly.
"""

from agent_toolkit.mcp.providers import shutdown_mcp_clients
from agent_toolkit.tools.catalog import ToolCatalog, ToolSelection
from agent_toolkit.tools.prompts import MCPPromptClient, PromptDefinition
from agent_toolkit.tools.registry import (
    DEFAULT_TOOL_REGISTRY,
    RegisteredTool,
    ToolDefinition,
    ToolDetailLevel,
    ToolRegistry,
    register_tool,
    registered_tool,
)
from agent_toolkit.tools.resources import MCPResourceClient
from agent_toolkit.tools.strands_tools import (
    STRANDS_TOOL_GROUPS,
    STRANDS_TOOLS_CATALOG,
    get_strands_tool_group,
    get_strands_tools,
    import_strands_tool,
    list_available_tools,
    list_tool_groups,
)

__all__ = [
    "DEFAULT_TOOL_REGISTRY",
    "STRANDS_TOOLS_CATALOG",
    "STRANDS_TOOL_GROUPS",
    "MCPPromptClient",
    "MCPResourceClient",
    "PromptDefinition",
    "RegisteredTool",
    "ToolCatalog",
    "ToolDefinition",
    "ToolDetailLevel",
    "ToolRegistry",
    "ToolSelection",
    "get_strands_tool_group",
    "get_strands_tools",
    "import_strands_tool",
    "list_available_tools",
    "list_tool_groups",
    "register_tool",
    "registered_tool",
    "shutdown_mcp_clients",
]
