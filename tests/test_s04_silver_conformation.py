"""S-04 · two ad networks, two conventions, one typed model with no NULL and no surprise."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.clickhouse_client import query_clickhouse, run_make
from tests.docker_engine import needs_docker_engine

GRAIN = "source, account_id, report_date, campaign_id, product_id"
SILVER_ROW_COUNT = 3030
UNKNOWN_PRODUCT_ID = "__unknown__"

PIVOT_ACCOUNT_ID = "acct_01"
PIVOT_CAMPAIGN_ID = "camp_003"
PIVOT_REPORT_DATE = "2026-07-15"
FLAGSHIP_PRODUCT_ID = "sku_77"
RESTATEMENT_EXTRACTION_DAY = "2026-08-20"

DAILY_EXTRACTION_DAYS = ("2026-07-15", "2026-07-16", "2026-07-17")
LOADED_TABLES = ("bronze.google_ads_raw", "bronze.meta_ads_raw", "silver.ads_daily")

PIVOT_CAMPAIGN_DAY = (
    f"account_id = '{PIVOT_ACCOUNT_ID}'"
    f" AND campaign_id = '{PIVOT_CAMPAIGN_ID}'"
    f" AND report_date = '{PIVOT_REPORT_DATE}'"
)

pytestmark = [
    pytest.mark.foundation,
    needs_docker_engine,
    pytest.mark.usefixtures("conformed_silver"),
]


@pytest.fixture(scope="session")
def conformed_silver() -> None:
    """Ingest the whole `mini` fixture into Bronze, then conform it into Silver."""
    run_make("up", "fixture")
    for table in LOADED_TABLES:
        query_clickhouse(f"TRUNCATE TABLE {table}")
    for source in ("google_ads", "meta_ads"):
        for extraction_day in DAILY_EXTRACTION_DAYS:
            ingest(source, extraction_day)
    ingest("google_ads", RESTATEMENT_EXTRACTION_DAY)
    run_make("silver")


def ingest(source: str, extraction_day: str) -> None:
    run_make("ingest", f"SOURCE={source}", f"EXTRACTED_AT={extraction_day}")


def silver(expression: str, predicate: str = "1") -> str:
    return query_clickhouse(
        f"SELECT {expression} FROM silver.ads_daily FINAL WHERE {predicate}"  # noqa: S608
    )


def amount(expression: str, predicate: str = "1") -> Decimal:
    return Decimal(silver(expression, predicate))


def test_r1_each_source_converts_its_own_amount_into_spend_eur() -> None:
    assert amount(
        "spend_eur",
        f"source = 'google_ads' AND {PIVOT_CAMPAIGN_DAY} AND product_id = '{FLAGSHIP_PRODUCT_ID}'",
    ) == Decimal("1234.500000")
    assert amount("spend_eur", f"source = 'meta_ads' AND {PIVOT_CAMPAIGN_DAY}") == Decimal(
        "987.650000"
    )


def test_r2_a_dimension_missing_at_the_source_becomes_an_explicit_sentinel() -> None:
    meta_day = f"source = 'meta_ads' AND report_date = '{PIVOT_REPORT_DATE}'"
    assert silver("count()", meta_day) == "10"
    assert silver(f"countIf(product_id = '{UNKNOWN_PRODUCT_ID}')", meta_day) == "10"

    nullable_columns = query_clickhouse(
        "SELECT groupArray(name) FROM system.columns"
        " WHERE database = 'silver' AND table = 'ads_daily' AND type LIKE '%Nullable%'"
    )
    assert nullable_columns == "[]"


def test_r3_report_date_comes_from_the_report_not_from_the_extraction() -> None:
    restated = (
        f"source = 'google_ads' AND _extracted_at = '{RESTATEMENT_EXTRACTION_DAY}'"
        f" AND product_id = '{FLAGSHIP_PRODUCT_ID}'"
    )
    assert silver("count()", restated) == "1"
    assert silver("min(report_date)", restated) == PIVOT_REPORT_DATE
    assert silver(f"countIf(report_date = '{RESTATEMENT_EXTRACTION_DAY}')") == "0"


def test_r4_silver_exposes_exactly_one_row_per_business_key() -> None:
    assert silver("count()") == str(SILVER_ROW_COUNT)
    assert silver(f"count() = countDistinct({GRAIN})") == "1"


def test_r5_the_conformation_makes_the_two_ad_networks_addable() -> None:
    assert amount("sum(spend_eur)", PIVOT_CAMPAIGN_DAY) == Decimal("13332.650000")
