"""S-01 · the foundation is convergent, reproducible after teardown, free of floating tags."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from tests.docker_engine import needs_docker_engine

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
COMMAND_TIMEOUT_SECONDS = 900
COUNT_MEDALLION_TABLES_QUERY = (
    "SELECT count() FROM system.tables WHERE database IN ('bronze', 'silver', 'gold')"
)
BRONZE_BASELINE_FINGERPRINT_QUERY = "SELECT count(), sum(cityHash64(*)) FROM bronze.ads_raw"


def _run(command: list[str]) -> str:
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


needs_running_stack = pytest.mark.foundation


def run_make(*targets: str) -> str:
    return _run(["make", *targets])


def query_clickhouse(query: str) -> str:
    inside_container = ["docker", "compose", "exec", "-T", "clickhouse", "clickhouse-client"]
    return _run([*inside_container, "--query", query]).strip()


def container_ids() -> list[str]:
    return sorted(_run(["docker", "compose", "ps", "--all", "--quiet"]).split())


def medallion_table_count() -> str:
    return query_clickhouse(COUNT_MEDALLION_TABLES_QUERY)


def bronze_baseline_fingerprint() -> str:
    return query_clickhouse(BRONZE_BASELINE_FINGERPRINT_QUERY)


def test_r3_no_image_version_is_floating() -> None:
    images = re.findall(r"^\s*image:\s*(\S+)", COMPOSE_FILE.read_text("utf-8"), re.MULTILINE)
    assert images, "no image declared in docker-compose.yml"
    assert [i for i in images if ":latest" in i] == []
    unpinned = [i for i in images if not re.search(r":[^:/]+$", i)]
    assert unpinned == [], f"images without an explicit tag: {unpinned}"


@needs_running_stack
@needs_docker_engine
def test_r1_make_up_is_convergent() -> None:
    run_make("up")
    container_ids_before = container_ids()
    table_count_before = medallion_table_count()

    run_make("up")

    assert container_ids() == container_ids_before, "a container was recreated"
    assert medallion_table_count() == table_count_before


@needs_running_stack
@needs_docker_engine
def test_r2_environment_is_reproducible_after_teardown() -> None:
    run_make("up", "seed")
    reference_fingerprint = bronze_baseline_fingerprint()

    run_make("down")
    run_make("up", "seed")

    assert bronze_baseline_fingerprint() == reference_fingerprint
