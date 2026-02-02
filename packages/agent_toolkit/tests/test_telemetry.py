from agent_toolkit.hooks import ToolTelemetry


def test_tool_telemetry_toggle() -> None:
    telemetry = ToolTelemetry()
    assert telemetry.allow_tools is True
    telemetry.set_allow_tools(False)
    assert telemetry.allow_tools is False
