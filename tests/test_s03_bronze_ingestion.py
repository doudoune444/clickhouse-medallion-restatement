"""S-03 · reloading an extraction leaves Bronze identical, neighbours included."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.docker_engine import needs_docker_engine

REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIO = "scenarios/S-03-bronze-extraction-reload.sh"
SCENARIO_TIMEOUT_SECONDS = 900
REPLAY_COUNT = 3


@pytest.mark.foundation
@needs_docker_engine
def test_the_four_assertions_stay_green_on_every_replay() -> None:
    for replay in range(REPLAY_COUNT):
        completed = subprocess.run(  # noqa: S603
            ["bash", SCENARIO],  # noqa: S607
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=SCENARIO_TIMEOUT_SECONDS,
            check=False,
        )
        assert completed.returncode == 0, f"replay {replay + 1} failed:\n{completed.stderr}"
