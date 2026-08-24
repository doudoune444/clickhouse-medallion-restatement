"""S-06 · Gold stores the components of the business metrics and reconciles with Silver."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from tests.clickhouse_client import query_clickhouse, run_make
from tests.docker_engine import needs_docker_engine

if TYPE_CHECKING:
    from collections.abc import Iterator

COMPONENT_COLUMNS = ("spend_eur", "clicks", "impressions", "conversions", "revenue_eur")
RATIO_COLUMNS = ("roas", "cpa", "ctr", "cpc")

PIVOT_SOURCE = "google_ads"
PIVOT_ACCOUNT_ID = "acct_01"
PIVOT_CAMPAIGN_ID = "camp_003"
PIVOT_REPORT_DATE = "2026-07-15"

DAILY_EXTRACTION_DAYS = ("2026-07-15", "2026-07-16", "2026-07-17")
SOURCES = ("google_ads", "meta_ads")
LOADED_TABLES = (
    "bronze.google_ads_raw",
    "bronze.meta_ads_raw",
    "silver.ads_daily",
    "gold.campaign_daily",
)

# A campaign-day with no spend and no revenue: the only way to read a ratio whose
# denominator is zero without forging one in the fixture the other stories rely on.
ZERO_DENOMINATOR_SOURCE = "zero_denominator_probe"
ZERO_DENOMINATOR_REPORT_DATE = "2026-01-01"
ZERO_DENOMINATOR_PARTITION_ID = "202601"

PIVOT_CAMPAIGN_DAY = (
    f"source = '{PIVOT_SOURCE}'"
    f" AND account_id = '{PIVOT_ACCOUNT_ID}'"
    f" AND campaign_id = '{PIVOT_CAMPAIGN_ID}'"
    f" AND report_date = '{PIVOT_REPORT_DATE}'"
)

pytestmark = [
    pytest.mark.foundation,
    needs_docker_engine,
    pytest.mark.usefixtures("rebuilt_gold"),
]


@pytest.fixture(scope="session")
def rebuilt_gold() -> None:
    """Ingest the whole `mini` fixture, conform it into Silver, rebuild Gold from it."""
    run_make("up", "fixture")
    for table in LOADED_TABLES:
        query_clickhouse(f"TRUNCATE TABLE {table}")
    for source in SOURCES:
        for extraction_day in DAILY_EXTRACTION_DAYS:
            run_make("ingest", f"SOURCE={source}", f"EXTRACTED_AT={extraction_day}")
    run_make("silver", "gold")


@pytest.fixture
def zero_denominator_campaign_day() -> Iterator[str]:
    """A forged all-zero row, dropped with its own partition once the ratios are read."""
    query_clickhouse(
        "INSERT INTO gold.campaign_daily VALUES"  # noqa: S608
        f" ('{ZERO_DENOMINATOR_SOURCE}', '{PIVOT_ACCOUNT_ID}', '{PIVOT_CAMPAIGN_ID}',"
        f" '{ZERO_DENOMINATOR_REPORT_DATE}', 0, 0, 0, 0, 0)"
    )
    try:
        yield f"source = '{ZERO_DENOMINATOR_SOURCE}'"
    finally:
        query_clickhouse(
            f"ALTER TABLE gold.campaign_daily DROP PARTITION ID '{ZERO_DENOMINATOR_PARTITION_ID}'"
        )


def gold_columns() -> list[str]:
    listed = query_clickhouse(
        "SELECT groupArray(name) FROM system.columns"
        " WHERE database = 'gold' AND table = 'campaign_daily'"
    )
    return listed.strip("[]").replace("'", "").split(",")


def metric(expression: str, predicate: str) -> str:
    return query_clickhouse(
        f"SELECT {expression} FROM gold.campaign_daily_metrics WHERE {predicate}"  # noqa: S608
    )


def test_r1_gold_stores_the_components_never_the_ratios() -> None:
    columns = gold_columns()
    for component in COMPONENT_COLUMNS:
        assert component in columns
    for ratio in RATIO_COLUMNS:
        assert ratio not in columns


def test_r2_the_derived_metrics_are_ratios_of_sums() -> None:
    assert Decimal(metric("roas", PIVOT_CAMPAIGN_DAY)) == Decimal("5.0000")
    assert Decimal(metric("cpa", PIVOT_CAMPAIGN_DAY)) == Decimal("30.862500")
    assert Decimal(metric("ctr", PIVOT_CAMPAIGN_DAY)) == Decimal("0.020000")
    assert Decimal(metric("cpc", PIVOT_CAMPAIGN_DAY)) == Decimal("0.617250")


def test_r3_gold_reconciles_exactly_with_silver() -> None:
    summed = ", ".join(f"sum({component})" for component in COMPONENT_COLUMNS)
    from_gold = query_clickhouse(f"SELECT {summed} FROM gold.campaign_daily")  # noqa: S608
    from_silver = query_clickhouse(f"SELECT {summed} FROM silver.ads_daily FINAL")  # noqa: S608
    assert from_gold == from_silver


def test_r4_a_zero_denominator_yields_null_rather_than_a_misleading_value(
    zero_denominator_campaign_day: str,
) -> None:
    for ratio in RATIO_COLUMNS:
        assert metric(ratio, zero_denominator_campaign_day) == "\\N"
