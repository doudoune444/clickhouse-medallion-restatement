"""`google_ads` convention: spend in micros, one row per product, date in `segments_date`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pyarrow as pa

from fixture_generator.money import AMOUNT_TYPE, euros
from fixture_generator.specification import (
    ACCOUNT_IDS,
    CAMPAIGN_IDS,
    FLAGSHIP_PRODUCT_ID,
    PIVOT_ACCOUNT_ID,
    PIVOT_CAMPAIGN_ID,
    PRODUCT_IDS,
)

if TYPE_CHECKING:
    import random
    from collections.abc import Sequence
    from datetime import date

SOURCE_NAME = "google_ads"


@dataclass(frozen=True)
class Metrics:
    """What one campaign-day is worth, before it is shared out between products."""

    cost_micros: int
    clicks: int
    impressions: int
    conversions: int
    revenue_cents: int

    def share_of(self, points: int) -> Metrics:
        """Return the slice of the campaign-day owed to a product holding `points`."""
        return Metrics(
            cost_micros=self.cost_micros * points // SHARE_POINTS_PER_CAMPAIGN_DAY,
            clicks=self.clicks * points // SHARE_POINTS_PER_CAMPAIGN_DAY,
            impressions=self.impressions * points // SHARE_POINTS_PER_CAMPAIGN_DAY,
            conversions=self.conversions * points // SHARE_POINTS_PER_CAMPAIGN_DAY,
            revenue_cents=self.revenue_cents * points // SHARE_POINTS_PER_CAMPAIGN_DAY,
        )


CAMPAIGN_DAY_TOTALS = Metrics(
    cost_micros=12_345_000_000,
    clicks=20_000,
    impressions=1_000_000,
    conversions=400,
    revenue_cents=6_172_500,
)
SHARE_POINTS_PER_CAMPAIGN_DAY = 100
FLAGSHIP_PRODUCT_SHARE_POINTS = 10

RESTATED_CONVERSIONS = 47
RESTATED_REVENUE_CENTS = 725_000

COLUMN_TYPES: dict[str, pa.DataType] = {
    "account_id": pa.string(),
    "campaign_id": pa.string(),
    "product_id": pa.string(),
    "segments_date": pa.date32(),
    "cost_micros": pa.int64(),
    "clicks": pa.int64(),
    "impressions": pa.int64(),
    "conversions": pa.int64(),
    "revenue_eur": AMOUNT_TYPE,
}
SCHEMA = pa.schema(COLUMN_TYPES)


@dataclass(frozen=True)
class Row:
    """One line of a `google_ads` product report."""

    account_id: str
    campaign_id: str
    product_id: str
    segments_date: date
    metrics: Metrics


def build_daily_report(generator: random.Random, report_day: date) -> pa.Table:
    """Return the report `google_ads` publishes for `report_day`, one row per product."""
    rows: list[Row] = []
    for account_id in ACCOUNT_IDS:
        for campaign_id in CAMPAIGN_IDS:
            share_points = _draw_share_points(generator)
            rows.extend(
                Row(
                    account_id=account_id,
                    campaign_id=campaign_id,
                    product_id=product_id,
                    segments_date=report_day,
                    metrics=CAMPAIGN_DAY_TOTALS.share_of(share_points[product_id]),
                )
                for product_id in PRODUCT_IDS
            )
    return _to_table(rows)


def build_restatement(report_day: date) -> pa.Table:
    """Return the late correction `google_ads` publishes for the flagship product."""
    corrected = CAMPAIGN_DAY_TOTALS.share_of(FLAGSHIP_PRODUCT_SHARE_POINTS)
    row = Row(
        account_id=PIVOT_ACCOUNT_ID,
        campaign_id=PIVOT_CAMPAIGN_ID,
        product_id=FLAGSHIP_PRODUCT_ID,
        segments_date=report_day,
        metrics=Metrics(
            cost_micros=corrected.cost_micros,
            clicks=corrected.clicks,
            impressions=corrected.impressions,
            conversions=RESTATED_CONVERSIONS,
            revenue_cents=RESTATED_REVENUE_CENTS,
        ),
    )
    return _to_table([row])


def _draw_share_points(generator: random.Random) -> dict[str, int]:
    """Hand the flagship product its fixed share, then scatter the rest at random."""
    share_points = dict.fromkeys(PRODUCT_IDS, 0)
    share_points[FLAGSHIP_PRODUCT_ID] = FLAGSHIP_PRODUCT_SHARE_POINTS
    challengers = [product_id for product_id in PRODUCT_IDS if product_id != FLAGSHIP_PRODUCT_ID]
    for _ in range(SHARE_POINTS_PER_CAMPAIGN_DAY - FLAGSHIP_PRODUCT_SHARE_POINTS):
        share_points[generator.choice(challengers)] += 1
    return share_points


def _to_table(rows: Sequence[Row]) -> pa.Table:
    return pa.table(
        {
            "account_id": [row.account_id for row in rows],
            "campaign_id": [row.campaign_id for row in rows],
            "product_id": [row.product_id for row in rows],
            "segments_date": [row.segments_date for row in rows],
            "cost_micros": [row.metrics.cost_micros for row in rows],
            "clicks": [row.metrics.clicks for row in rows],
            "impressions": [row.metrics.impressions for row in rows],
            "conversions": [row.metrics.conversions for row in rows],
            "revenue_eur": [euros(row.metrics.revenue_cents) for row in rows],
        },
        schema=SCHEMA,
    )
