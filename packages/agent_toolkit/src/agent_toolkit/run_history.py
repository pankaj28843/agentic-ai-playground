from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class RunSnapshot:
    """Snapshot of a completed run."""

    run_id: str
    mode: str
    profile: str
    session_id: str
    resource_uri: str
    prompt: str
    output: str
    tool_events: list[dict[str, str]]
    started_at: str
    finished_at: str
    metrics: dict | None = None


@dataclass(frozen=True)
class RunMetadata:
    """Derived metadata for a run snapshot."""

    duration_seconds: int
    duration_label: str
    tool_count: int
    output_size: int
    output_size_label: str


def write_snapshot(snapshot: RunSnapshot, base_dir: str = ".runs") -> Path:
    """Write a run snapshot to disk."""
    output_dir = Path(base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{snapshot.run_id}.json"
    path.write_text(json.dumps(asdict(snapshot), indent=2), encoding="utf-8")
    return path


def list_snapshots(base_dir: str = ".runs") -> list[RunSnapshot]:
    """List run snapshots from disk."""
    directory = Path(base_dir)
    if not directory.exists():
        return []
    snapshots: list[RunSnapshot] = []
    for path in directory.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "tool_events" not in data:
            data["tool_events"] = []
        for event in data["tool_events"]:
            if isinstance(event, dict) and "ts" not in event:
                event["ts"] = ""
        # Handle missing metrics field in older snapshots
        if "metrics" not in data:
            data["metrics"] = None
        snapshots.append(RunSnapshot(**data))
    return sorted(snapshots, key=lambda item: item.finished_at, reverse=True)


def compute_run_metadata(snapshot: RunSnapshot) -> RunMetadata:
    """Compute derived metadata for UI and exports."""
    started = _parse_timestamp(snapshot.started_at)
    finished = _parse_timestamp(snapshot.finished_at)
    duration_seconds = 0
    if started and finished:
        duration_seconds = max(0, int((finished - started).total_seconds()))
    tool_count = len(snapshot.tool_events)
    output_size = len(snapshot.output)
    return RunMetadata(
        duration_seconds=duration_seconds,
        duration_label=_format_duration(duration_seconds),
        tool_count=tool_count,
        output_size=output_size,
        output_size_label=_format_output_size(output_size),
    )


def new_run_id() -> str:
    """Create a new run id based on current UTC time."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    cleaned = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _format_duration(duration_seconds: int) -> str:
    if duration_seconds <= 0:
        return "0s"
    minutes, seconds = divmod(duration_seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s" if minutes else f"{seconds}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def _format_output_size(output_size: int) -> str:
    if output_size < 1000:
        return f"{output_size}c"
    return f"{output_size // 1000}k"
