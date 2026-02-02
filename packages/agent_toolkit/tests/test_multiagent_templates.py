from agent_toolkit.multiagent import _load_graph_templates, _load_swarm_templates


def test_graph_templates_load() -> None:
    """Test that graph templates load from config."""
    graphs = _load_graph_templates()
    # Should have at least one graph template
    assert len(graphs) > 0
    # Check that templates have expected structure
    for template in graphs.values():
        assert template.get("nodes") is not None
        assert "edges" in template  # Key must exist even if empty


def test_swarm_templates_load() -> None:
    """Test that swarm templates load from config."""
    swarms = _load_swarm_templates()
    # Should have at least one swarm template
    assert len(swarms) > 0
    # Check that templates have expected structure
    for template in swarms.values():
        assert template.get("agents") is not None
