#!/usr/bin/env python3
"""Restart the frontend compose stack with configurable deployment modes.

Modes:
  - Default (no flags): Development servers (pnpm dev + uvicorn --reload) in daemon mode
  - --watch: Same + Docker Compose file sync for live reload without rebuild

Both modes run development servers. Use --watch for automatic file sync into containers.

Logs are streamed to ./logs/frontend/ organized by date with automatic pruning.
Each service (web, api) gets its own log file with timestamps.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

# Default log retention period in days
DEFAULT_LOG_RETENTION_DAYS = 14

# PID file for tracking log streaming processes
LOG_STREAMER_PID_FILE = ".log-streamer.pid"

# Polling interval for watch-mode config restarts (seconds)
WATCH_CONFIG_POLL_SECONDS = 1.0

# Configurable via the LOCAL_TZ environment variable, defaults to Europe/Copenhagen.
# If the configured timezone is invalid, fall back to the system's local timezone.
_LOCAL_TZ_NAME = os.getenv("LOCAL_TZ", "Europe/Copenhagen")
try:
    LOCAL_TZ = ZoneInfo(_LOCAL_TZ_NAME)
except Exception:  # noqa: BLE001
    # Fall back to system local timezone, or Europe/Copenhagen if unavailable
    from datetime import datetime

    LOCAL_TZ = datetime.now().astimezone().tzinfo or ZoneInfo("Europe/Copenhagen")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Restart the frontend compose stack.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s              # Dev servers (pnpm dev + uvicorn --reload) in daemon mode
  %(prog)s --watch      # Same + Docker Compose file sync (live reload)
  %(prog)s --no-build   # Start without rebuilding images
  %(prog)s --down-only  # Only stop the stack, don't start
  %(prog)s --logs       # Start and follow logs in terminal

Modes:
  Default: Dev servers in daemon mode (rebuild image to pick up changes)
  --watch: Dev servers + file sync (changes reflected without rebuild)

Log Management:
  Logs are streamed to ./logs/frontend/<date>/<service>_<timestamp>.log
  Each service gets its own timestamped log file.
  Old logs are pruned automatically (default: 14 days retention).
""",
    )

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Enable Docker Compose file sync for live reload (foreground)",
    )
    mode_group.add_argument(
        "-f",
        "--foreground",
        action="store_true",
        help="Run in foreground without file sync",
    )
    mode_group.add_argument(
        "--down-only",
        action="store_true",
        help="Only stop the stack, don't start it",
    )

    # Build options
    build_group = parser.add_mutually_exclusive_group()
    build_group.add_argument(
        "--build",
        action="store_true",
        default=True,
        help="Build images before starting (default)",
    )
    build_group.add_argument(
        "--no-build",
        action="store_true",
        help="Don't build images before starting",
    )

    # Log management options
    parser.add_argument(
        "--no-log-stream",
        action="store_true",
        help="Skip streaming container logs to files",
    )
    parser.add_argument(
        "--log-retention-days",
        type=int,
        default=DEFAULT_LOG_RETENTION_DAYS,
        metavar="DAYS",
        help=f"Days to retain log files (default: {DEFAULT_LOG_RETENTION_DAYS})",
    )
    parser.add_argument(
        "--skip-log-prune",
        action="store_true",
        help="Skip pruning old log files",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help="Custom log directory (default: ./logs/frontend)",
    )

    # Additional options
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Force recreation of containers even if unchanged",
    )
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="Don't start linked services",
    )
    parser.add_argument(
        "--pull",
        choices=["always", "missing", "never"],
        default="missing",
        help="Pull image policy (default: missing)",
    )
    parser.add_argument(
        "-l",
        "--logs",
        action="store_true",
        help="Follow logs in terminal after starting in daemon mode",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        metavar="SECONDS",
        help="Timeout for container shutdown (default: 30)",
    )
    parser.add_argument(
        "--skip-port-cleanup",
        action="store_true",
        help="Skip killing processes on conflicting ports",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Restart the frontend compose stack."""
    args = parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    _load_dotenv(repo_root / ".env")
    frontend_dir = repo_root / "frontend"
    compose_file = frontend_dir / "compose.yaml"
    logs_config_file = frontend_dir / "compose.logs.yaml"
    watch_file = frontend_dir / "compose.watch.yaml"

    # Set up log directory
    log_dir = args.log_dir or (repo_root / "logs" / "frontend")

    if not compose_file.exists():
        message = f"Missing compose file: {compose_file}"
        raise FileNotFoundError(message)

    docker_path = _docker_path()

    # Use frontend dir as project directory since compose.yaml uses context: ..
    # which should resolve relative to the compose file location
    base_cmd = [
        docker_path,
        "compose",
        "--project-directory",
        str(frontend_dir),
        "-f",
        str(compose_file),
    ]

    # Add logging config if available
    if logs_config_file.exists():
        base_cmd.extend(["-f", str(logs_config_file)])

    # Prune old log files before starting
    if not args.skip_log_prune:
        _prune_old_logs(
            log_dir,
            retention_days=args.log_retention_days,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

    # Stop any existing log streaming processes
    _stop_log_streamers(log_dir, dry_run=args.dry_run, verbose=args.verbose)

    # Export existing container logs before stopping (if containers are running)
    _export_container_logs(
        base_cmd,
        log_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    # Build images first to minimize downtime (build while old containers still running)
    if not args.no_build:
        _compose_build(base_cmd, dry_run=args.dry_run, verbose=args.verbose)

    # Stop existing stack (now that new images are ready)
    _compose_down(base_cmd, timeout=args.timeout, dry_run=args.dry_run, verbose=args.verbose)

    if args.down_only:
        if args.verbose:
            sys.stderr.write("Stack stopped (--down-only specified)\n")
        return 0

    # Free up ports
    if not args.skip_port_cleanup:
        _free_ports({10000, 10001}, dry_run=args.dry_run, verbose=args.verbose)

    # Build the up command
    up_cmd = list(base_cmd)

    # Handle watch mode
    watch_supported = False
    if args.watch:
        watch_supported = _supports_watch(docker_path, base_cmd, watch_file)
        if watch_supported:
            up_cmd.extend(["-f", str(watch_file)])
        else:
            _warn_missing_watch(watch_supported, watch_file)

    up_cmd.append("up")

    # Don't add --build flag since we already built above (minimizes downtime)

    # Add watch flag if requested and supported
    if args.watch and watch_supported:
        up_cmd.append("--watch")

    # Add daemon mode unless watch or foreground
    is_daemon_mode = not args.watch and not args.foreground
    if is_daemon_mode:
        up_cmd.append("-d")

    # Add optional flags
    if args.force_recreate:
        up_cmd.append("--force-recreate")
    if args.no_deps:
        up_cmd.append("--no-deps")
    if args.pull != "missing":
        up_cmd.extend(["--pull", args.pull])

    if args.dry_run:
        sys.stderr.write(f"[dry-run] Would execute: {' '.join(up_cmd)}\n")
        if is_daemon_mode and not args.no_log_stream:
            sys.stderr.write(f"[dry-run] Would start log streaming to: {log_dir}\n")
        return 0

    if args.verbose:
        sys.stderr.write(f"Executing: {' '.join(up_cmd)}\n")

    if args.watch and watch_supported:
        return _run_watch_with_restarts(
            base_cmd,
            up_cmd,
            repo_root=repo_root,
            frontend_dir=frontend_dir,
            watch_file=watch_file,
            timeout=args.timeout,
            no_build=args.no_build,
            verbose=args.verbose,
        )

    _run_or_raise(up_cmd)

    # Start background log streaming for daemon mode
    if is_daemon_mode and not args.no_log_stream:
        _start_log_streamers(
            base_cmd,
            log_dir,
            services=["web", "api"],
            verbose=args.verbose,
        )

    # Follow logs in terminal if requested (only makes sense in daemon mode)
    if args.logs and is_daemon_mode:
        logs_cmd = [*base_cmd, "logs", "-f"]
        if args.verbose:
            sys.stderr.write(f"Following logs: {' '.join(logs_cmd)}\n")
        _run_or_raise(logs_cmd)

    return 0


# -----------------------------------------------------------------------------
# Log Streaming Functions
# -----------------------------------------------------------------------------


def _get_log_file_path(log_dir: Path, service: str) -> Path:
    """Generate a timestamped log file path organized by date and service.

    Creates directory structure: log_dir/YYYY-MM-DD/service_HH-MM-SS.log
    Uses local timezone (Europe/Copenhagen) for timestamps.
    """
    now = datetime.now(tz=LOCAL_TZ)
    date_dir = log_dir / now.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    timestamp = now.strftime("%H-%M-%S")
    return date_dir / f"{service}_{timestamp}.log"


def _start_log_streamers(
    base_cmd: list[str],
    log_dir: Path,
    services: list[str],
    *,
    verbose: bool = False,
) -> None:
    """Start background processes to stream logs for each service to files.

    Uses `stdbuf -oL docker compose logs -f ... | tee -a <file>` for real-time
    unbuffered log streaming. This approach:
    - Writes logs to files in real-time (line-buffered via stdbuf)
    - Keeps logs visible via `docker compose logs` command
    - Works well for development workflows

    Stores PIDs in a file for cleanup on next restart.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    pid_file = log_dir / LOG_STREAMER_PID_FILE
    pids: list[int] = []

    # Check for required tools
    stdbuf_path = shutil.which("stdbuf")
    tee_path = shutil.which("tee")

    if not stdbuf_path or not tee_path:
        # Fall back to direct file streaming (buffered)
        if verbose:
            missing = []
            if not stdbuf_path:
                missing.append("stdbuf")
            if not tee_path:
                missing.append("tee")
            sys.stderr.write(
                f"Warning: {', '.join(missing)} not found; falling back to buffered log streaming\n"
            )
        _start_log_streamers_fallback(base_cmd, log_dir, services, verbose=verbose)
        return

    for service in services:
        log_file = _get_log_file_path(log_dir, service)

        # Write header to log file before starting stream
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with log_file.open("a", encoding="utf-8") as f:
                f.write(f"# Log stream started: {datetime.now(tz=LOCAL_TZ).isoformat()}\n")
                f.write(f"# Service: {service}\n")
                f.write("# " + "=" * 70 + "\n\n")
        except OSError as e:
            sys.stderr.write(f"Warning: Failed to write log header for {service}: {e}\n")
            continue

        # Build the command using stdbuf for line-buffered output piped to tee
        # stdbuf -oL forces line buffering on stdout
        # tee -a appends to file while also outputting to stdout (which we discard)
        logs_cmd = [*base_cmd, "logs", "-f", "--timestamps", "--no-color", service]
        shell_cmd = (
            f"{stdbuf_path} -oL {' '.join(shlex.quote(c) for c in logs_cmd)} "
            f"2>&1 | {tee_path} -a {shlex.quote(str(log_file))} > /dev/null"
        )

        if verbose:
            sys.stderr.write(f"Starting log stream: {service} -> {log_file}\n")

        try:
            # Start background shell process for the pipeline
            # Security: shell=True is safe here as we control all command components
            process = subprocess.Popen(  # noqa: S602
                shell_cmd,
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # Detach from terminal
            )

            pids.append(process.pid)

            if verbose:
                sys.stderr.write(f"  PID {process.pid}: streaming to {log_file.name}\n")

        except OSError as e:
            sys.stderr.write(f"Warning: Failed to start log stream for {service}: {e}\n")

    # Save PIDs for cleanup
    if pids:
        pid_file.write_text("\n".join(str(pid) for pid in pids), encoding="utf-8")
        if verbose:
            sys.stderr.write(f"Log streaming started for {len(pids)} services\n")


def _start_log_streamers_fallback(
    base_cmd: list[str],
    log_dir: Path,
    services: list[str],
    *,
    verbose: bool = False,
) -> None:
    """Fallback log streaming using direct file output (buffered).

    Used when stdbuf/tee are not available. Logs may not appear in real-time.
    """
    pid_file = log_dir / LOG_STREAMER_PID_FILE
    pids: list[int] = []

    for service in services:
        log_file = _get_log_file_path(log_dir, service)
        logs_cmd = [*base_cmd, "logs", "-f", "--timestamps", "--no-color", service]

        if verbose:
            sys.stderr.write(f"Starting log stream (buffered): {service} -> {log_file}\n")

        try:
            log_handle = log_file.open("a", encoding="utf-8")
            log_handle.write(f"# Log stream started: {datetime.now(tz=LOCAL_TZ).isoformat()}\n")
            log_handle.write(f"# Service: {service}\n")
            log_handle.write(f"# Command: {' '.join(logs_cmd)}\n")
            log_handle.write("# " + "=" * 70 + "\n\n")
            log_handle.flush()

            process = subprocess.Popen(
                logs_cmd,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )

            pids.append(process.pid)

            if verbose:
                sys.stderr.write(f"  PID {process.pid}: streaming to {log_file.name}\n")

        except OSError as e:
            sys.stderr.write(f"Warning: Failed to start log stream for {service}: {e}\n")

    if pids:
        pid_file.write_text("\n".join(str(pid) for pid in pids), encoding="utf-8")
        if verbose:
            sys.stderr.write(f"Log streaming started for {len(pids)} services\n")


def _stop_log_streamers(
    log_dir: Path,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    """Stop any running log streaming processes from previous runs."""
    pid_file = log_dir / LOG_STREAMER_PID_FILE

    if not pid_file.exists():
        return

    try:
        pids_text = pid_file.read_text(encoding="utf-8").strip()
        if not pids_text:
            return

        pids = [int(p) for p in pids_text.splitlines() if p.strip().isdigit()]
    except (OSError, ValueError):
        return

    stopped = 0
    for pid in pids:
        try:
            if dry_run:
                sys.stderr.write(f"[dry-run] Would stop log streamer PID {pid}\n")
                stopped += 1
                continue

            # Check if process exists
            os.kill(pid, 0)

            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)
            stopped += 1

            if verbose:
                sys.stderr.write(f"Stopped log streamer PID {pid}\n")

        except ProcessLookupError:
            # Process already gone
            pass
        except PermissionError:
            sys.stderr.write(f"Warning: Cannot stop PID {pid} (permission denied)\n")

    # Clean up PID file
    if not dry_run:
        with contextlib.suppress(OSError):
            pid_file.unlink()

    if stopped > 0 and verbose:
        action = "Would stop" if dry_run else "Stopped"
        sys.stderr.write(f"{action} {stopped} log streamer(s)\n")


def _export_container_logs(
    base_cmd: list[str],
    log_dir: Path,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    """Export logs from running containers before stopping them.

    Uses `docker compose logs --timestamps --no-color` for clean log output.
    Creates a snapshot of current logs before restart.
    """
    # Check if any containers are running
    ps_result = subprocess.run(
        [*base_cmd, "ps", "-q"],
        check=False,
        capture_output=True,
        text=True,
    )

    if not ps_result.stdout.strip():
        if verbose:
            sys.stderr.write("No running containers, skipping log export\n")
        return

    log_file = _get_log_file_path(log_dir, "snapshot")

    if dry_run:
        sys.stderr.write(f"[dry-run] Would export logs to: {log_file}\n")
        return

    if verbose:
        sys.stderr.write(f"Exporting container logs to: {log_file}\n")

    # Export logs with timestamps, no color for clean file output
    logs_cmd = [*base_cmd, "logs", "--timestamps", "--no-color"]

    try:
        result = subprocess.run(
            logs_cmd,
            check=False,
            capture_output=True,
            text=True,
        )

        # Create log directory if needed
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Write both stdout and stderr to log file
        with log_file.open("w", encoding="utf-8") as f:
            f.write(f"# Log snapshot (pre-restart): {datetime.now(tz=LOCAL_TZ).isoformat()}\n")
            f.write(f"# Command: {' '.join(logs_cmd)}\n")
            f.write("# " + "=" * 70 + "\n\n")

            if result.stdout:
                f.write(result.stdout)

            if result.stderr:
                f.write("\n# STDERR:\n")
                f.write(result.stderr)

        if verbose:
            sys.stderr.write(f"Exported {log_file.stat().st_size} bytes to {log_file}\n")

    except OSError as e:
        sys.stderr.write(f"Warning: Failed to export logs: {e}\n")


def _prune_old_logs(
    log_dir: Path,
    *,
    retention_days: int = DEFAULT_LOG_RETENTION_DAYS,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    """Remove log files older than retention_days.

    Removes empty date directories after pruning.
    """
    if not log_dir.exists():
        return

    cutoff = datetime.now(tz=LOCAL_TZ) - timedelta(days=retention_days)
    pruned_count = 0
    pruned_bytes = 0

    # Iterate through date directories (YYYY-MM-DD format)
    for date_dir in sorted(log_dir.iterdir()):
        if not date_dir.is_dir():
            continue

        # Try to parse directory name as date
        try:
            dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d").replace(tzinfo=LOCAL_TZ)
        except ValueError:
            continue  # Skip non-date directories

        # Check if directory is older than cutoff
        if dir_date < cutoff:
            if dry_run:
                # Count files that would be deleted
                for log_file in date_dir.glob("*.log"):
                    pruned_count += 1
                    pruned_bytes += log_file.stat().st_size
                sys.stderr.write(f"[dry-run] Would remove: {date_dir}\n")
            else:
                # Remove all files in the directory
                for log_file in date_dir.glob("*.log"):
                    try:
                        pruned_bytes += log_file.stat().st_size
                        log_file.unlink()
                        pruned_count += 1
                    except OSError:
                        pass  # Ignore errors during cleanup

                # Remove the empty directory
                with contextlib.suppress(OSError):
                    date_dir.rmdir()

    if pruned_count > 0 and verbose:
        size_str = _format_bytes(pruned_bytes)
        action = "Would prune" if dry_run else "Pruned"
        sys.stderr.write(f"{action} {pruned_count} log files ({size_str})\n")


def _format_bytes(num_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024  # type: ignore[assignment]
    return f"{num_bytes:.1f} TB"


# -----------------------------------------------------------------------------
# Compose Version and Watch Support
# -----------------------------------------------------------------------------


class _ComposeVersion(NamedTuple):
    major: int
    minor: int
    patch: int


def _watch_min_version(watch_file: Path) -> _ComposeVersion:
    min_version = _ComposeVersion(2, 22, 0)
    try:
        watch_text = watch_file.read_text(encoding="utf-8")
        if "sync+restart" in watch_text:
            min_version = _ComposeVersion(2, 23, 0)
        if "sync+exec" in watch_text:
            min_version = _ComposeVersion(2, 32, 0)
        if re.search(r"^\s*action:\s*restart\s*(?:#.*)?$", watch_text, re.MULTILINE):
            min_version = _ComposeVersion(2, 32, 0)
    except OSError:
        # Fall back to the base minimum when the watch file is unavailable.
        pass
    return min_version


def _supports_watch(
    docker_path: str,
    base_cmd: list[str],
    watch_file: Path,
) -> bool:
    if not watch_file.exists():
        return False

    min_version = _watch_min_version(watch_file)
    version = _compose_version(docker_path)
    if version < min_version:
        return False

    return _compose_accepts_watch(base_cmd, watch_file)


def _compose_version(docker_path: str) -> _ComposeVersion:
    try:
        result = subprocess.run(
            [docker_path, "compose", "version", "--short"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return _ComposeVersion(0, 0, 0)

    raw = result.stdout.strip().lstrip("v")
    parts = raw.split(".")
    try:
        major, minor, patch = (int(part) for part in parts[:3])
    except ValueError:
        return _ComposeVersion(0, 0, 0)
    return _ComposeVersion(major, minor, patch)


def _compose_accepts_watch(base_cmd: list[str], watch_file: Path) -> bool:
    try:
        subprocess.run(
            [*base_cmd, "-f", str(watch_file), "config"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return False
    return True


def _warn_missing_watch(supported: bool, watch_file: Path) -> None:
    min_version = _watch_min_version(watch_file)
    if not watch_file.exists():
        message = f"Compose watch file missing: {watch_file}"
    elif not supported:
        message = (
            "Compose watch is not supported by the current Docker Compose CLI. "
            f"Starting without watch; requires v{min_version.major}.{min_version.minor}.{min_version.patch}+."
        )
    else:
        return
    sys.stderr.write(f"{message}\n")


# -----------------------------------------------------------------------------
# Watch Mode: Config Change Restart Logic
# -----------------------------------------------------------------------------


class _WatchTarget(NamedTuple):
    path: Path
    action: str  # "restart" or "rebuild"


class _FileFingerprint(NamedTuple):
    exists: bool
    mtime_ns: int
    size: int


def _fingerprint(path: Path) -> _FileFingerprint:
    try:
        stat = path.stat()
        return _FileFingerprint(True, stat.st_mtime_ns, stat.st_size)
    except FileNotFoundError:
        return _FileFingerprint(False, 0, 0)


def _watch_targets(repo_root: Path, frontend_dir: Path, watch_file: Path) -> list[_WatchTarget]:
    compose_file = frontend_dir / "compose.yaml"
    logs_file = frontend_dir / "compose.logs.yaml"
    nginx_conf = frontend_dir / "nginx" / "nginx.conf"
    env_file = repo_root / ".env"

    targets: list[_WatchTarget] = [
        _WatchTarget(compose_file, "rebuild"),
        _WatchTarget(watch_file, "restart"),
        _WatchTarget(logs_file, "restart"),
        _WatchTarget(env_file, "restart"),
        _WatchTarget(nginx_conf, "restart"),
    ]

    return targets


def _run_watch_with_restarts(
    base_cmd: list[str],
    up_cmd: list[str],
    *,
    repo_root: Path,
    frontend_dir: Path,
    watch_file: Path,
    timeout: int,
    no_build: bool,
    verbose: bool = False,
) -> int:
    """Run `docker compose up --watch` and restart when config files change."""
    targets = _watch_targets(repo_root, frontend_dir, watch_file)
    fingerprints = {target.path: _fingerprint(target.path) for target in targets}

    should_exit = False

    def _handle_signal(signum: int, frame: object | None = None) -> None:  # noqa: ARG001
        nonlocal should_exit
        should_exit = True

    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        while True:
            if verbose:
                sys.stderr.write("Starting compose watch...\n")

            process = subprocess.Popen(up_cmd)

            while True:
                if should_exit:
                    _terminate_process(process, timeout=timeout, verbose=verbose)
                    return 0

                return_code = process.poll()
                if return_code is not None:
                    return return_code

                changed_targets: list[_WatchTarget] = []
                for target in targets:
                    current = _fingerprint(target.path)
                    if current != fingerprints[target.path]:
                        fingerprints[target.path] = current
                        changed_targets.append(target)

                if changed_targets:
                    rebuild_needed = any(t.action == "rebuild" for t in changed_targets)
                    changed_list = ", ".join(str(t.path) for t in changed_targets)
                    if verbose:
                        sys.stderr.write(f"Config change detected: {changed_list}\n")

                    _terminate_process(process, timeout=timeout, verbose=verbose)

                    if rebuild_needed and not no_build:
                        if verbose:
                            sys.stderr.write("Rebuilding images due to config change...\n")
                        _compose_build(base_cmd, verbose=verbose)

                    _compose_down(base_cmd, timeout=timeout, verbose=verbose)
                    break

                time.sleep(WATCH_CONFIG_POLL_SECONDS)
    finally:
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)


def _terminate_process(
    process: subprocess.Popen[bytes] | subprocess.Popen[str], *, timeout: int, verbose: bool
) -> None:
    if process.poll() is not None:
        return
    if verbose:
        sys.stderr.write("Stopping compose watch...\n")
    try:
        process.send_signal(signal.SIGINT)
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout)


# -----------------------------------------------------------------------------
# Docker and Process Management
# -----------------------------------------------------------------------------


def _docker_path() -> str:
    docker_path = shutil.which("docker")
    if docker_path is None:
        message = "docker is not installed or not on PATH"
        raise RuntimeError(message)
    return docker_path


def _compose_build(
    base_cmd: list[str],
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    """Build images before stopping the stack to minimize downtime."""
    cmd = [*base_cmd, "build"]
    if dry_run:
        sys.stderr.write(f"[dry-run] Would execute: {' '.join(cmd)}\n")
        return
    if verbose:
        sys.stderr.write(f"Building images: {' '.join(cmd)}\n")
    _run_or_raise(cmd)


def _compose_down(
    base_cmd: list[str],
    *,
    timeout: int = 30,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    cmd = [*base_cmd, "down", "--remove-orphans", "-t", str(timeout)]
    if dry_run:
        sys.stderr.write(f"[dry-run] Would execute: {' '.join(cmd)}\n")
        return
    if verbose:
        sys.stderr.write(f"Stopping stack: {' '.join(cmd)}\n")
    _run_or_raise(cmd)


def _free_ports(
    ports: set[int],
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    port_to_pids = _ports_to_pids(ports)
    if not port_to_pids:
        return

    allowed = ("vite", "uvicorn", "assistant_web_backend")
    for port, pids in port_to_pids.items():
        for pid in pids:
            command = _pid_command(pid)
            if not command or not any(token in command for token in allowed):
                sys.stderr.write(f"Port {port} still in use by pid {pid}; command: {command}\n")
                continue
            if dry_run:
                sys.stderr.write(f"[dry-run] Would terminate pid {pid} ({command})\n")
                continue
            _terminate_pid_process(pid, command, verbose=verbose)

    if not dry_run:
        remaining = _ports_to_pids(ports)
        if remaining:
            sys.stderr.write("Ports remain in use after cleanup; run `ss -ltnp` to inspect.\n")


def _ports_to_pids(ports: set[int]) -> dict[int, list[int]]:
    port_to_pids: dict[int, list[int]] = {}
    ss_path = _tool_path("ss")
    result = subprocess.run(
        [ss_path, "-ltnp"],
        check=False,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        for port in ports:
            if f":{port} " not in line and not line.endswith(f":{port}"):
                continue
            pid = _parse_pid(line)
            if pid is None:
                continue
            port_to_pids.setdefault(port, []).append(pid)
    return port_to_pids


def _parse_pid(line: str) -> int | None:
    marker = "pid="
    if marker not in line:
        return None
    segment = line.split(marker, maxsplit=1)[1]
    digits = []
    for char in segment:
        if char.isdigit():
            digits.append(char)
        else:
            break
    if not digits:
        return None
    return int("".join(digits))


def _pid_command(pid: int) -> str:
    ps_path = _tool_path("ps")
    result = subprocess.run(
        [ps_path, "-p", str(pid), "-o", "cmd="],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _terminate_pid_process(pid: int, command: str, *, verbose: bool = False) -> None:
    if verbose:
        sys.stderr.write(f"Stopping pid {pid} ({command})\n")
    kill_path = _tool_path("kill")
    try:
        subprocess.run([kill_path, "-TERM", str(pid)], check=False)
        time.sleep(2)  # Allow graceful shutdown before SIGKILL
        subprocess.run([kill_path, "-KILL", str(pid)], check=False)
    except OSError:
        # Process may have already exited; ignore cleanup failures
        return


def _run_or_raise(command: list[str]) -> None:
    result = subprocess.run(
        command,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command)


def _tool_path(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        message = f"Required tool not found: {name}"
        raise RuntimeError(message)
    return path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    repo_root = path.parent  # .env is at repo root

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        stripped = stripped.removeprefix("export ")
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue

        # Resolve PLAYGROUND_CONFIG_DIR to absolute path (relative to repo root)
        if key == "PLAYGROUND_CONFIG_DIR" and not Path(value).is_absolute():
            value = str((repo_root / value).resolve())

        os.environ.setdefault(key, value)


if __name__ == "__main__":
    sys.exit(main())
