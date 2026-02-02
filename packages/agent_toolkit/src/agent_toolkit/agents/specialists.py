from __future__ import annotations

import logging
from typing import Any

from strands import Agent

from agent_toolkit.tools.registry import registered_tool

logger = logging.getLogger(__name__)

# System prompt for TechDocs specialist - derived from agents.toml deep research patterns
TECHDOCS_SPECIALIST_PROMPT = """
You are a TECHDOCS RESEARCH SPECIALIST. You are called as a tool by other agents to perform focused documentation research.

## YOUR MISSION
When given a research query, perform THOROUGH documentation research and return a comprehensive answer with code examples and citations.

## TECHDOCS WORKFLOW (mandatory)

### Step 1: Discover Tenants (1-3 calls)
```
find_tenant("topic") → Returns tenant codenames
```
Always start here. For a Django question, search "django" AND "python".

### Step 2: Search Multiple Angles (5-10 calls)
```
root_search(tenant, query) → Returns URLs with snippets
```
Search from DIFFERENT angles:
- Exact terms from the user's question
- Related concepts (e.g., "temporary files" for file upload questions)
- Error messages or class names mentioned

### Step 3: Fetch Full Pages (5-10 calls)
```
root_fetch(tenant, url) → Returns full page content
```
Snippets are NOT enough. Fetch 5-10 pages to get complete information.

### Step 4: Synthesize
Combine findings into a working solution with:
- Clear explanation of the solution
- Complete, runnable code examples
- Citations for every claim (URL + what was learned)

## TOOL CALL BUDGET
- Maximum: 50 tool calls per research task
- Target: 3 find_tenant + 8 searches + 8 fetches = ~19 calls
- STOP after 10 fetches - synthesize with what you have

## OUTPUT FORMAT
Return a structured answer:

### Summary
[2-3 sentence direct answer]

### Solution
[Detailed explanation with code]

```python
# Complete, runnable code example
```

### Sources
- [URL 1]: [key insight learned]
- [URL 2]: [key insight learned]

### Notes
[Any caveats, edge cases, or version-specific info]

## QUALITY REQUIREMENTS
- NEVER guess when you can search
- ALWAYS cite sources for technical claims
- Code examples must be COMPLETE and RUNNABLE
- Cross-reference between tenants (django + python, react + typescript)
"""


def _get_techdocs_tools() -> list[Any]:
    """Get TechDocs MCP client as tool provider."""
    try:
        from agent_toolkit.mcp.providers import get_techdocs_client  # noqa: PLC0415

        return [get_techdocs_client()]
    except Exception:  # noqa: BLE001 - graceful fallback for missing MCP
        logger.warning("TechDocs MCP client unavailable for specialist")
        return []


@registered_tool(
    description=(
        "Delegate documentation research to a specialist agent. "
        "Use for any technical question requiring official documentation lookup. "
        "The specialist will search TechDocs (Django, Python, React, FastAPI, etc.), "
        "read full pages, and return a comprehensive answer with code examples and citations."
    ),
    category="agents",
    tags=("techdocs", "specialist", "research", "documentation"),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The research query. Be specific about what you need. "
                    "Example: 'How to convert Django InMemoryUploadedFile to a file path "
                    "for libraries that require LoadFromFile()'"
                ),
            }
        },
        "required": ["query"],
    },
    output_schema={"type": "string"},
    capabilities=("delegate", "read"),
    source="agent:techdocs_specialist",
)
def techdocs_specialist(query: str) -> str:
    """Perform focused TechDocs research and return comprehensive answer.

    This is an "agent as tool" - a specialized sub-agent that can be called
    by the main agent to perform deep documentation research.

    Args:
        query: The research query to investigate

    Returns:
        Comprehensive answer with code examples and citations
    """
    tools = _get_techdocs_tools()
    if not tools:
        return "TechDocs MCP client unavailable - check TECHDOCS_MCP_URL configuration"

    agent = Agent(
        system_prompt=TECHDOCS_SPECIALIST_PROMPT,
        tools=tools,
        callback_handler=None,
    )
    try:
        result = agent(query)
    except Exception as exc:  # noqa: BLE001 - surface error in tool response
        message = str(exc)
        if "botocore[crt]" in message or "Missing Dependency" in message:
            return "Bedrock requires botocore[crt]; install with uv sync --all-packages"
        if "ResourceNotFoundException" in message and "ConverseStream" in message:
            return (
                "Bedrock model access missing; request model access/use-case details "
                "or set BEDROCK_MODEL_ID to an enabled model"
            )
        if "Input Tokens Exceeded" in message:
            return (
                "Research exceeded context limit. Try a more specific query "
                "or break the question into smaller parts."
            )
        return f"TechDocs specialist failed: {message}"

    # Extract the response text
    output = getattr(result, "output", None) or getattr(result, "message", None) or str(result)
    return str(output)
