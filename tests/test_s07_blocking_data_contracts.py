"""S-07 · data contracts fail loudly on a non-conforming layer and block the publication."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from tests.clickhouse_client import REPO_ROOT, query_clickhouse, run_make
from tests.docker_engine import needs_docker_engine

if TYPE_CHECKING:
    from collections.abc import Iterator

CONTRACT_TIMEOUT_SECONDS = 900

UNIQUENESS_CONTRACT = "010_grain_uniqueness"
RECONCILIATION_CONTRACT = "020_layer_reconciliation"
PLAUSIBILITY_CONTRACT = "030_metric_plausibility"
PLAUSIBILITY_RULE = "clicks <= impressions"

PIVOT_SOURCE = "google_ads"
PIVOT_ACCOUNT_ID = "acct_01"
PIVOT_CAMPAIGN_ID = "camp_003"
PIVOT_REPORT_DATE = "2026-07-15"
FIXTURE_PARTITION_ID = "202607"

# The forged rows live in a month of their own, so dropping that partition undoes them
# without touching the fixture the assertions of the other stories read.
PROBE_REPORT_DATE = "2026-01-01"
PROBE_PARTITION_ID = "202601"
DUPLICATE_PROBE_SOURCE = "duplicate_grain_probe"
IMPLAUSIBLE_PROBE_SOURCE = "implausible_metric_probe"
IMPLAUSIBLE_CLICKS = 500
IMPLAUSIBLE_IMPRESSIONS = 100

DAILY_EXTRACTION_DAYS = ("2026-07-15", "2026-07-16", "2026-07-17")
SOURCES = ("google_ads", "meta_ads")
LOADED_TABLES = (
    "bronze.google_ads_raw",
    "bronze.meta_ads_raw",
    "silver.ads_daily",
    "gold.campaign_daily",
)

pytestmark = [
    pytest.mark.foundation,
    needs_docker_engine,
    pytest.mark.usefixtures("published_pipeline"),
]


@pytest.fixture(scope="session")
def published_pipeline() -> None:
    """Ingest the whole `mini` fixture, conform it into Silver, publish Gold from it."""
    run_make("up", "fixture")
    for table in LOADED_TABLES:
        query_clickhouse(f"TRUNCATE TABLE {table}")
    for source in SOURCES:
        for extraction_day in DAILY_EXTRACTION_DAYS:
            run_make("ingest", f"SOURCE={source}", f"EXTRACTED_AT={extraction_day}")
    run_make("silver", "gold")


def evaluate_contracts() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "contracts"],  # noqa: S607
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=CONTRACT_TIMEOUT_SECONDS,
        check=False,
    )


def rebuild_gold() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "gold"],  # noqa: S607
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=CONTRACT_TIMEOUT_SECONDS,
        check=False,
    )


def failure_report(contract_name: str, evaluation: subprocess.CompletedProcess[str]) -> str:
    """The block a failing contract prints: its FAILED line and the violations under it."""
    lines = evaluation.stdout.splitlines()
    headers = [index for index, line in enumerate(lines) if "contract" in line]
    for position, index in enumerate(headers):
        if contract_name in lines[index] and "FAILED" in lines[index]:
            end = headers[position + 1] if position + 1 < len(headers) else len(lines)
            return "\n".join(lines[index:end])
    return ""


@pytest.fixture
def duplicated_gold_grain() -> Iterator[None]:
    """Two Gold rows sharing one grain, carrying no figures: uniqueness alone is broken."""
    for _ in range(2):
        query_clickhouse(
            "INSERT INTO gold.campaign_daily VALUES"  # noqa: S608
            f" ('{DUPLICATE_PROBE_SOURCE}', '{PIVOT_ACCOUNT_ID}', '{PIVOT_CAMPAIGN_ID}',"
            f" '{PROBE_REPORT_DATE}', 0, 0, 0, 0, 0)"
        )
    try:
        yield
    finally:
        query_clickhouse(
            f"ALTER TABLE gold.campaign_daily DROP PARTITION ID '{PROBE_PARTITION_ID}'"
        )


@pytest.fixture
def double_counted_gold_partition() -> Iterator[None]:
    """The published month, counted twice — the failure a silent double count produces."""
    query_clickhouse(
        "INSERT INTO gold.campaign_daily"  # noqa: S608
        " SELECT * FROM gold.campaign_daily"
        f" WHERE toYYYYMM(report_date) = {FIXTURE_PARTITION_ID}"
    )
    try:
        yield
    finally:
        run_make("gold")


@pytest.fixture
def implausible_silver_row() -> Iterator[None]:
    """A Silver row reporting more clicks than impressions, waiting to be published."""
    query_clickhouse(
        "INSERT INTO silver.ads_daily VALUES"  # noqa: S608
        f" ('{IMPLAUSIBLE_PROBE_SOURCE}', '{PIVOT_ACCOUNT_ID}', '{PROBE_REPORT_DATE}',"
        f" '{PIVOT_CAMPAIGN_ID}', '__unknown__', 0, {IMPLAUSIBLE_CLICKS},"
        f" {IMPLAUSIBLE_IMPRESSIONS}, 0, 0, '{PROBE_REPORT_DATE}')"
    )
    try:
        yield
    finally:
        query_clickhouse(f"ALTER TABLE silver.ads_daily DROP PARTITION ID '{PROBE_PARTITION_ID}'")


def test_the_three_contracts_are_green_on_the_mini_fixture() -> None:
    evaluation = evaluate_contracts()
    assert evaluation.returncode == 0, evaluation.stdout
    for contract_name in (UNIQUENESS_CONTRACT, RECONCILIATION_CONTRACT, PLAUSIBILITY_CONTRACT):
        assert f"ok      {contract_name}" in evaluation.stdout


@pytest.mark.usefixtures("duplicated_gold_grain")
def test_r1_a_duplicated_grain_fails_the_uniqueness_contract() -> None:
    evaluation = evaluate_contracts()
    assert evaluation.returncode != 0
    report = failure_report(UNIQUENESS_CONTRACT, evaluation)
    assert PROBE_PARTITION_ID in report
    assert "gold" in report


@pytest.mark.usefixtures("double_counted_gold_partition")
def test_r2_a_double_counted_partition_fails_the_reconciliation_contract() -> None:
    evaluation = evaluate_contracts()
    assert evaluation.returncode != 0
    report = failure_report(RECONCILIATION_CONTRACT, evaluation)
    assert FIXTURE_PARTITION_ID in report


@pytest.mark.usefixtures("implausible_silver_row")
def test_r3_more_clicks_than_impressions_fails_the_plausibility_contract() -> None:
    evaluation = evaluate_contracts()
    assert evaluation.returncode != 0
    report = failure_report(PLAUSIBILITY_CONTRACT, evaluation)
    assert PLAUSIBILITY_RULE in report
    assert "silver" in report


@pytest.mark.usefixtures("implausible_silver_row")
def test_a_red_contract_blocks_the_publication_and_leaves_the_served_partition_alone() -> None:
    published_before = query_clickhouse(
        "SELECT sum(spend_eur), sum(clicks), sum(impressions), sum(conversions), sum(revenue_eur)"
        " FROM gold.campaign_daily"
    )

    rebuild = rebuild_gold()

    assert rebuild.returncode != 0
    assert "BLOCKED" in rebuild.stdout
    assert (
        query_clickhouse(
            "SELECT count() FROM gold.campaign_daily"  # noqa: S608
            f" WHERE toYYYYMM(report_date) = {PROBE_PARTITION_ID}"
        )
        == "0"
    )
    assert (
        query_clickhouse(
            "SELECT sum(spend_eur), sum(clicks), sum(impressions), sum(conversions),"
            " sum(revenue_eur) FROM gold.campaign_daily"
        )
        == published_before
    )
