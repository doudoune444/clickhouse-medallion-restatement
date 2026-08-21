"""Skip guard shared by the tests that drive the docker stack."""

from __future__ import annotations

import subprocess

import pytest

DOCKER_PROBE_TIMEOUT_SECONDS = 30


def _docker_engine_responds() -> bool:
    """The binary alone is not enough: under WSL the shim exists with no engine behind it."""
    try:
        probe = subprocess.run(
            ["docker", "compose", "version"],  # noqa: S607
            capture_output=True,
            timeout=DOCKER_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return probe.returncode == 0


needs_docker_engine = pytest.mark.skipif(
    not _docker_engine_responds(),
    reason="no docker engine on this machine: this test is verified by CI",
)
