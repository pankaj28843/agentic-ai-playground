import json

from agent_toolkit.run_history import (
    RunSnapshot,
    compute_run_metadata,
    list_snapshots,
    new_run_id,
    write_snapshot,
)


def test_write_and_list_snapshots(tmp_path) -> None:
    run_id = new_run_id()
    snapshot = RunSnapshot(
        run_id=run_id,
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
    write_snapshot(snapshot, base_dir=str(tmp_path))
    snapshots = list_snapshots(base_dir=str(tmp_path))
    assert snapshots[0].run_id == run_id


def test_list_snapshots_defaults_missing_tool_events(tmp_path) -> None:
    run_id = new_run_id()
    payload = {
        "run_id": run_id,
        "mode": "single",
        "profile": "techdocs",
        "session_id": "session-1",
        "resource_uri": "file:///resource",
        "prompt": "hello",
        "output": "result",
        "started_at": "2026-01-01T00:00:00Z",
        "finished_at": "2026-01-01T00:01:00Z",
    }
    path = tmp_path / f"{run_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    snapshots = list_snapshots(base_dir=str(tmp_path))
    assert snapshots[0].tool_events == []


def test_compute_run_metadata() -> None:
    snapshot = RunSnapshot(
        run_id="run-1",
        mode="single",
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
                "ts": "2026-01-01T00:00:30Z",
            }
        ],
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:01:00Z",
    )
    metadata = compute_run_metadata(snapshot)
    assert metadata.duration_seconds == 60
    assert metadata.duration_label == "1m 0s"
    assert metadata.tool_count == 1
    assert metadata.output_size == len(snapshot.output)
