"""Agent creation factory, builders, and specialist sub-agents.

This module provides:
- AgentFactory: Creates Strands agents from profiles
- build_conversation_manager/build_session_manager: Runtime component builders
- Specialist sub-agents that can be invoked as tools

The "agent as tool" pattern (Factor 10: Small, Focused Agents) allows complex
tasks to be delegated to specialized sub-agents with their own context windows
and tool sets.
"""

from agent_toolkit.agents.builders import build_conversation_manager, build_session_manager
from agent_toolkit.agents.factory import AgentFactory

__all__ = ["AgentFactory", "build_conversation_manager", "build_session_manager"]
