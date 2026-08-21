"""`meta_ads` convention: spend in euros, no product breakdown, date in `date_start`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pyarrow as pa

from fixture_generator.money import AMOUNT_TYPE, euros
from fixture_generator.specification import (
    ACCOUNT_IDS,
    CAMPAIGN_IDS,
    PIVOT_ACCOUNT_ID,
    PIVOT_CAMPAIGN_ID,
    PIVOT_REPORT_DAY,
)

if TYPE_CHECKING:
    import random
    from collections.abc import Sequence
    from datetime import date

SOURCE_NAME = "meta_ads"


@dataclass(frozen=True)
class Metrics:
    """What one campaign-day is worth on `meta_ads`, which reports no product."""

    spend_cents: int
    clicks: int
    impressions: int
    conversions: int
    revenue_cents: int

    def scaled_by(self, factor: int) -> Metrics:
        """Return the same campaign-day `factor` times as big, ratios untouched."""
        return Metrics(
            spend_cents=self.spend_cents * factor,
            clicks=self.clicks * factor,
            impressions=self.impressions * factor,
            conversions=self.conversions * factor,
            revenue_cents=self.revenue_cents * factor,
        )


PIVOT_CAMPAIGN_DAY = Metrics(
    spend_cents=98_765,
    clicks=1_500,
    impressions=80_000,
    conversions=25,
    revenue_cents=395_060,
)
PIVOT_SCALE_FACTOR = 1
CAMPAIGN_DAY_SCALE_FACTORS = (1, 2, 3, 4, 5)

COLUMN_TYPES: dict[str, pa.DataType] = {
    "account_id": pa.string(),
    "campaign_id": pa.string(),
    "date_start": pa.date32(),
    "spend": AMOUNT_TYPE,
    "clicks": pa.int64(),
    "impressions": pa.int64(),
    "conversions": pa.int64(),
    "revenue_eur": AMOUNT_TYPE,
}
SCHEMA = pa.schema(COLUMN_TYPES)


@dataclass(frozen=True)
class Row:
    """One line of a `meta_ads` campaign report."""

    account_id: str
    campaign_id: str
    date_start: date
    metrics: Metrics


def build_daily_report(generator: random.Random, report_day: date) -> pa.Table:
    """Return the report `meta_ads` publishes for `report_day`, one row per campaign."""
    rows = [
        Row(
            account_id=account_id,
            campaign_id=campaign_id,
            date_start=report_day,
            metrics=PIVOT_CAMPAIGN_DAY.scaled_by(
                _scale_factor_of(generator, account_id, campaign_id, report_day)
            ),
        )
        for account_id in ACCOUNT_IDS
        for campaign_id in CAMPAIGN_IDS
    ]
    return _to_table(rows)


def _scale_factor_of(
    generator: random.Random, account_id: str, campaign_id: str, report_day: date
) -> int:
    """The pivot campaign-day is worth exactly what the backlog pins; the rest varies."""
    is_pivot = (account_id, campaign_id, report_day) == (
        PIVOT_ACCOUNT_ID,
        PIVOT_CAMPAIGN_ID,
        PIVOT_REPORT_DAY,
    )
    if is_pivot:
        return PIVOT_SCALE_FACTOR
    return generator.choice(CAMPAIGN_DAY_SCALE_FACTORS)


def _to_table(rows: Sequence[Row]) -> pa.Table:
    return pa.table(
        {
            "account_id": [row.account_id for row in rows],
            "campaign_id": [row.campaign_id for row in rows],
            "date_start": [row.date_start for row in rows],
            "spend": [euros(row.metrics.spend_cents) for row in rows],
            "clicks": [row.metrics.clicks for row in rows],
            "impressions": [row.metrics.impressions for row in rows],
            "conversions": [row.metrics.conversions for row in rows],
            "revenue_eur": [euros(row.metrics.revenue_cents) for row in rows],
        },
        schema=SCHEMA,
    )
