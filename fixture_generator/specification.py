"""Dimensions and calendar shared by the two ad networks of `fixtures/mini`."""

from __future__ import annotations

from datetime import date, timedelta

REPORT_DAYS = (date(2026, 7, 14), date(2026, 7, 15), date(2026, 7, 16))
ACCOUNT_IDS = ("acct_01", "acct_02")
CAMPAIGN_IDS = ("camp_001", "camp_002", "camp_003", "camp_004", "camp_005")
PRODUCT_IDS = tuple(f"sku_{index:02d}" for index in range(100))

DAYS_BETWEEN_REPORT_AND_EXTRACTION = 1

FLAGSHIP_PRODUCT_ID = "sku_77"
PIVOT_ACCOUNT_ID = "acct_01"
PIVOT_CAMPAIGN_ID = "camp_003"
PIVOT_REPORT_DAY = date(2026, 7, 15)


def extraction_day_of(report_day: date) -> date:
    """Return the day an ad network publishes the report of `report_day`."""
    return report_day + timedelta(days=DAYS_BETWEEN_REPORT_AND_EXTRACTION)
