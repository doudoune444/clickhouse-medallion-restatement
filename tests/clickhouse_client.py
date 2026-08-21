"""Driving the running stack from a test: one make target, one SQL query."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMAND_TIMEOUT_SECONDS = 900
INSIDE_CONTAINER = ("docker", "compose", "exec", "-T", "clickhouse", "clickhouse-client")


def run(command: list[str]) -> str:
    """Run `command` at the repository root and return its standard output."""
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
        check=False,
    )
    assert completed.returncode == 0, (
        f"`{' '.join(command)}` failed ({completed.returncode}):\n{completed.stderr}"
    )
    return completed.stdout


def run_make(*targets: str) -> str:
    """Run make targets in order."""
    return run(["make", *targets])


def query_clickhouse(query: str) -> str:
    """Return the single trimmed answer ClickHouse gives to `query`."""
    return run([*INSIDE_CONTAINER, "--query", query]).strip()
