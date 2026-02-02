from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from agent_toolkit.run_history import RunSnapshot, compute_run_metadata, list_snapshots


def export_runs(run_dir: str = ".runs", export_dir: str = ".exports") -> Path:
    """Export run snapshots to a timestamped directory.

    Note: Evaluation report generation has been moved to agent_toolkit.evals.
    Use EvalRunner for evaluation functionality.
    """
    snapshots = list_snapshots(run_dir)
    if not snapshots:
        message = "No run snapshots found"
        raise RuntimeError(message)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    export_path = Path(export_dir) / timestamp
    export_path.mkdir(parents=True, exist_ok=True)

    snapshots_path = export_path / "snapshots"
    snapshots_path.mkdir(exist_ok=True)
    for snapshot in snapshots:
        (snapshots_path / f"{snapshot.run_id}.json").write_text(
            json.dumps(asdict(snapshot), indent=2),
            encoding="utf-8",
        )

    summary_markdown = render_run_summary_markdown(snapshots)
    (export_path / "summary.md").write_text(summary_markdown, encoding="utf-8")

    return export_path


def render_run_summary_markdown(snapshots: list[RunSnapshot]) -> str:
    """Render a Markdown summary of run metadata."""
    lines = ["# Run Summary", "", f"- Total runs: {len(snapshots)}", ""]
    lines.extend(
        [
            "| Run ID | Mode | Profile | Duration | Tools | Output | Finished |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for snapshot in snapshots:
        metadata = compute_run_metadata(snapshot)
        lines.append(
            "| "
            + " | ".join(
                [
                    snapshot.run_id,
                    snapshot.mode,
                    snapshot.profile,
                    metadata.duration_label,
                    str(metadata.tool_count),
                    metadata.output_size_label,
                    snapshot.finished_at,
                ]
            )
            + " |"
        )
    return "\n".join(lines)
