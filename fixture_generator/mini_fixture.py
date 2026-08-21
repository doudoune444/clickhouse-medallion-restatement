"""`fixtures/mini`: three days of two ad networks, plus the late correction of one day."""

from __future__ import annotations

import random
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from fixture_generator import google_ads_reports, meta_ads_reports
from fixture_generator.object_storage import report_object_key
from fixture_generator.parquet_writing import write_report
from fixture_generator.specification import (
    PIVOT_REPORT_DAY,
    REPORT_DAYS,
    extraction_day_of,
)

if TYPE_CHECKING:
    import pyarrow as pa

DEFAULT_SEED = 42
DEFAULT_DESTINATION = Path("fixtures/mini")

FIRST_PART_FILE_NAME = "part-0001.parquet"
RESTATEMENT_EXTRACTION_DAY = date(2026, 8, 20)
RESTATED_REPORT_DAY = PIVOT_REPORT_DAY


def write_mini_fixture(destination: Path, seed: int) -> list[str]:
    """Write the whole fixture under `destination` and return its object keys."""
    generator = random.Random(seed)  # noqa: S311
    object_keys = []
    for report_day in REPORT_DAYS:
        extraction_day = extraction_day_of(report_day)
        object_keys.append(
            _write(
                google_ads_reports.build_daily_report(generator, report_day),
                destination,
                report_object_key(
                    google_ads_reports.SOURCE_NAME, extraction_day, FIRST_PART_FILE_NAME
                ),
            )
        )
        object_keys.append(
            _write(
                meta_ads_reports.build_daily_report(generator, report_day),
                destination,
                report_object_key(
                    meta_ads_reports.SOURCE_NAME, extraction_day, FIRST_PART_FILE_NAME
                ),
            )
        )
    object_keys.append(
        _write(
            google_ads_reports.build_restatement(RESTATED_REPORT_DAY),
            destination,
            report_object_key(
                google_ads_reports.SOURCE_NAME,
                RESTATEMENT_EXTRACTION_DAY,
                f"restated_{RESTATED_REPORT_DAY:%Y-%m-%d}.parquet",
            ),
        )
    )
    return object_keys


def _write(table: pa.Table, destination: Path, object_key: str) -> str:
    write_report(table, destination / object_key)
    return object_key
