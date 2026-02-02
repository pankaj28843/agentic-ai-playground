from agent_toolkit.export import export_runs
from agent_toolkit.run_history import RunSnapshot, write_snapshot


def test_export_runs(tmp_path) -> None:
    snapshot = RunSnapshot(
        run_id="run-1",
        mode="graph",
        profile="techdocs",
        session_id="session-1",
        resource_uri="file:///resource",
        prompt="hello",
        output="result",
        tool_events=[
            {
                "name": "search",
                "input": "query",
                "output": "result",
                "ts": "2026-01-01T00:00:00Z",
            }
        ],
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:01:00Z",
    )
    runs_dir = tmp_path / "runs"
    exports_dir = tmp_path / "exports"
    write_snapshot(snapshot, base_dir=str(runs_dir))
    export_path = export_runs(run_dir=str(runs_dir), export_dir=str(exports_dir))
    # Verify summary is generated (report.md removed - use EvalRunner for evals)
    summary_path = export_path / "summary.md"
    assert summary_path.exists()
    assert "run-1" in summary_path.read_text(encoding="utf-8")
    # Verify snapshots directory
    assert (export_path / "snapshots").exists()
    assert (export_path / "snapshots" / "run-1.json").exists()
