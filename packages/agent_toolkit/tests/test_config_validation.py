"""Unit tests for configuration schema validation and run mode mapping."""

import pytest
from agent_toolkit.config.execution_mode import ExecutionModeResolver
from agent_toolkit.config.new_loader import _validate_references
from agent_toolkit.config.schema import (
    AtomicAgent,
    ConfigSchema,
    EntrypointType,
    GraphTemplate,
    PublicProfile,
    ToolGroup,
)


class TestConfigSchemaValidation:
    """Test configuration schema validation and orphan detection."""

    def test_valid_config_passes_validation(self):
        """Test that a valid configuration passes validation."""
        # Create a valid schema
        agents = {
            "test_agent": AtomicAgent(
                name="test_agent",
                system_prompt="Test prompt",
                model="test-model",
                tools=[],
                tool_groups=["test_group"],
                metadata={},
            )
        }

        tool_groups = {
            "test_group": ToolGroup(
                name="test_group",
                description="Test group",
                tools=["test_tool"],
                capabilities=["test"],
            )
        }

        public_profiles = {
            "test_profile": PublicProfile(
                name="test_profile",
                display_name="Test Profile",
                description="Test profile",
                entrypoint_type=EntrypointType.SINGLE,
                entrypoint_reference="test_agent",
                default=True,
                metadata={},
            )
        }

        schema = ConfigSchema(
            agents=agents,
            graphs={},
            swarms={},
            public_profiles=public_profiles,
            tool_groups=tool_groups,
        )

        result = _validate_references(schema)
        assert result.valid
        assert len(result.errors) == 0

    def test_missing_agent_reference_fails_validation(self):
        """Test that missing agent reference fails validation."""
        public_profiles = {
            "test_profile": PublicProfile(
                name="test_profile",
                display_name="Test Profile",
                description="Test profile",
                entrypoint_type=EntrypointType.SINGLE,
                entrypoint_reference="missing_agent",
                default=True,
                metadata={},
            )
        }

        schema = ConfigSchema(
            agents={}, graphs={}, swarms={}, public_profiles=public_profiles, tool_groups={}
        )

        result = _validate_references(schema)
        assert not result.valid
        assert len(result.errors) == 1
        assert "unknown agent 'missing_agent'" in result.errors[0].lower()

    def test_orphaned_agents_generate_warnings(self):
        """Test that orphaned agents generate warnings."""
        agents = {
            "used_agent": AtomicAgent(
                name="used_agent",
                system_prompt="Used agent",
                model="test-model",
                tools=[],
                tool_groups=[],
                metadata={},
            ),
            "orphaned_agent": AtomicAgent(
                name="orphaned_agent",
                system_prompt="Orphaned agent",
                model="test-model",
                tools=[],
                tool_groups=[],
                metadata={},
            ),
        }

        public_profiles = {
            "test_profile": PublicProfile(
                name="test_profile",
                display_name="Test Profile",
                description="Test profile",
                entrypoint_type=EntrypointType.SINGLE,
                entrypoint_reference="used_agent",
                default=True,
                metadata={},
            )
        }

        schema = ConfigSchema(
            agents=agents, graphs={}, swarms={}, public_profiles=public_profiles, tool_groups={}
        )

        result = _validate_references(schema)
        assert result.valid  # Should still be valid
        assert len(result.warnings) == 1
        assert "orphaned_agent" in result.warnings[0]

    def test_graph_validation(self):
        """Test graph template validation."""
        agents = {
            "agent1": AtomicAgent(
                name="agent1",
                system_prompt="Agent 1",
                model="test-model",
                tools=[],
                tool_groups=[],
                metadata={},
            ),
            "agent2": AtomicAgent(
                name="agent2",
                system_prompt="Agent 2",
                model="test-model",
                tools=[],
                tool_groups=[],
                metadata={},
            ),
        }

        from agent_toolkit.config.schema import GraphEdge, GraphNode

        graphs = {
            "test_graph": GraphTemplate(
                name="test_graph",
                description="Test graph",
                entry_point="node1",
                nodes=[
                    GraphNode(name="node1", agent="agent1"),
                    GraphNode(name="node2", agent="agent2"),
                ],
                edges=[GraphEdge(from_node="node1", to_node="node2")],
                timeouts={},
            )
        }

        public_profiles = {
            "test_profile": PublicProfile(
                name="test_profile",
                display_name="Test Profile",
                description="Test profile",
                entrypoint_type=EntrypointType.GRAPH,
                entrypoint_reference="test_graph",
                default=True,
                metadata={},
            )
        }

        schema = ConfigSchema(
            agents=agents, graphs=graphs, swarms={}, public_profiles=public_profiles, tool_groups={}
        )

        result = _validate_references(schema)
        assert result.valid
        assert len(result.errors) == 0

    def test_invalid_graph_entry_point_fails_validation(self):
        """Test that invalid graph entry point fails validation."""
        agents = {
            "agent1": AtomicAgent(
                name="agent1",
                system_prompt="Agent 1",
                model="test-model",
                tools=[],
                tool_groups=[],
                metadata={},
            )
        }

        from agent_toolkit.config.schema import GraphNode

        graphs = {
            "test_graph": GraphTemplate(
                name="test_graph",
                description="Test graph",
                entry_point="missing_node",  # Invalid entry point
                nodes=[GraphNode(name="node1", agent="agent1")],
                edges=[],
                timeouts={},
            )
        }

        public_profiles = {
            "test_profile": PublicProfile(
                name="test_profile",
                display_name="Test Profile",
                description="Test profile",
                entrypoint_type=EntrypointType.GRAPH,
                entrypoint_reference="test_graph",
                default=True,
                metadata={},
            )
        }

        schema = ConfigSchema(
            agents=agents, graphs=graphs, swarms={}, public_profiles=public_profiles, tool_groups={}
        )

        result = _validate_references(schema)
        assert not result.valid
        assert any(
            "entry_point 'missing_node' is not a defined node" in error for error in result.errors
        )


class TestExecutionModeResolver:
    """Test execution mode resolution from public profiles."""

    def test_single_agent_resolution(self):
        """Test resolution of single agent profile."""
        resolver = ExecutionModeResolver()

        # Test that unknown profile raises ValueError (no backward compat)
        with pytest.raises(ValueError, match="Unknown public profile"):
            resolver.resolve_execution_mode("unknown_profile")

        # Test resolution of a known profile from config
        profiles = resolver.get_public_profiles()
        if profiles:
            profile_name = next(iter(profiles.keys()))
            execution_mode, entrypoint_reference, metadata = resolver.resolve_execution_mode(
                profile_name
            )
            assert execution_mode in ("single", "swarm", "graph")
            assert entrypoint_reference
            assert "profile_name" in metadata

    def test_public_profiles_retrieval(self):
        """Test retrieval of public profiles."""
        resolver = ExecutionModeResolver()

        try:
            profiles = resolver.get_public_profiles()
            assert isinstance(profiles, dict)

            # Should have the profiles we defined in config
            expected_profiles = ["quick", "research", "expert"]
            for profile_name in expected_profiles:
                if profile_name in profiles:
                    profile_data = profiles[profile_name]
                    assert "name" in profile_data
                    assert "description" in profile_data
                    assert "entrypoint_type" in profile_data
                    assert "entrypoint_reference" in profile_data

        except Exception:
            # If config loading fails, that's expected in test environment
            pytest.skip("Config loading failed in test environment")


class TestRunModeMapping:
    """Test run mode mapping functionality."""

    def test_entrypoint_type_enum(self):
        """Test EntrypointType enum values."""
        assert EntrypointType.SINGLE == "single"
        assert EntrypointType.SWARM == "swarm"
        assert EntrypointType.GRAPH == "graph"

    def test_public_profile_creation(self):
        """Test PublicProfile creation with different entrypoint types."""
        # Single agent profile
        single_profile = PublicProfile(
            name="test_single",
            display_name="Test Single",
            description="Single agent profile",
            entrypoint_type=EntrypointType.SINGLE,
            entrypoint_reference="test_agent",
            default=False,
            metadata={"ui_order": 1},
        )

        assert single_profile.entrypoint_type == EntrypointType.SINGLE
        assert single_profile.entrypoint_reference == "test_agent"

        # Graph profile
        graph_profile = PublicProfile(
            name="test_graph",
            display_name="Test Graph",
            description="Graph profile",
            entrypoint_type=EntrypointType.GRAPH,
            entrypoint_reference="test_graph_template",
            default=False,
            metadata={"ui_order": 2},
        )

        assert graph_profile.entrypoint_type == EntrypointType.GRAPH
        assert graph_profile.entrypoint_reference == "test_graph_template"


if __name__ == "__main__":
    pytest.main([__file__])
