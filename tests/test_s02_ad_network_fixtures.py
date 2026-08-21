"""S-02 · the fixture is reproducible, the two ad networks disagree on purpose."""

from __future__ import annotations

import hashlib
import os
import subprocess
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from fixture_generator.mini_fixture import DEFAULT_SEED, write_mini_fixture
from fixture_generator.object_storage import LAKE_BUCKET, create_lake_client

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMAND_TIMEOUT_SECONDS = 900

GOOGLE_DAY_KEY = (
    "raw/source=google_ads/report=campaign_daily/extracted_at=2026-07-16/part-0001.parquet"
)
META_DAY_KEY = "raw/source=meta_ads/report=campaign_daily/extracted_at=2026-07-16/part-0001.parquet"
RESTATEMENT_KEY = (
    "raw/source=google_ads/report=campaign_daily"
    "/extracted_at=2026-08-20/restated_2026-07-15.parquet"
)

PIVOT_ACCOUNT_ID = "acct_01"
PIVOT_CAMPAIGN_ID = "camp_003"
FLAGSHIP_PRODUCT_ID = "sku_77"

needs_lake_credentials = pytest.mark.skipif(
    "MINIO_ROOT_USER" not in os.environ,
    reason="the lake credentials are exported by make, this test needs `make test`",
)


@pytest.fixture(scope="session")
def mini_fixture(tmp_path_factory: pytest.TempPathFactory) -> Path:
    destination = tmp_path_factory.mktemp("mini")
    write_mini_fixture(destination, DEFAULT_SEED)
    return destination


def read(root: Path, object_key: str) -> pa.Table:
    return pq.read_table(root / object_key)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def campaign_day_rows(table: pa.Table) -> list[dict[str, object]]:
    return [
        row
        for row in table.to_pylist()
        if row["account_id"] == PIVOT_ACCOUNT_ID and row["campaign_id"] == PIVOT_CAMPAIGN_ID
    ]


def column_total(rows: list[dict[str, object]], column: str) -> Decimal:
    return sum((Decimal(str(row[column])) for row in rows), start=Decimal(0))


def test_r1_one_seed_produces_the_same_bytes(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"

    object_keys = write_mini_fixture(first, DEFAULT_SEED)
    assert write_mini_fixture(second, DEFAULT_SEED) == object_keys

    digests = {key: (sha256_of(first / key), sha256_of(second / key)) for key in object_keys}
    assert [key for key, (left, right) in digests.items() if left != right] == []


def test_r2_each_source_keeps_its_own_conventions(mini_fixture: Path) -> None:
    google = read(mini_fixture, GOOGLE_DAY_KEY).schema
    meta = read(mini_fixture, META_DAY_KEY).schema

    assert google.field("cost_micros").type == pa.int64()
    assert google.field("product_id").type == pa.string()
    assert google.field("segments_date").type == pa.date32()

    assert meta.field("spend").type == pa.decimal128(18, 2)
    assert meta.field("date_start").type == pa.date32()
    assert "product_id" not in meta.names
    assert "cost_micros" not in meta.names


def test_r3_volumes_and_pivot_values_follow_the_specification(mini_fixture: Path) -> None:
    google = read(mini_fixture, GOOGLE_DAY_KEY)
    meta = read(mini_fixture, META_DAY_KEY)

    assert google.num_rows == 1000
    assert meta.num_rows == 10

    campaign_day = campaign_day_rows(google)
    flagship = next(row for row in campaign_day if row["product_id"] == FLAGSHIP_PRODUCT_ID)
    assert flagship["cost_micros"] == 1_234_500_000
    assert flagship["clicks"] == 2_000
    assert flagship["impressions"] == 100_000
    assert flagship["conversions"] == 40
    assert flagship["revenue_eur"] == Decimal("6172.50")

    assert len(campaign_day) == 100
    assert column_total(campaign_day, "cost_micros") == 12_345_000_000
    assert column_total(campaign_day, "clicks") == 20_000
    assert column_total(campaign_day, "impressions") == 1_000_000
    assert column_total(campaign_day, "conversions") == 400
    assert column_total(campaign_day, "revenue_eur") == Decimal("61725.00")

    meta_pivot = next(iter(campaign_day_rows(meta)))
    assert str(meta_pivot["spend"]) == "987.65"
    assert meta_pivot["clicks"] == 1_500
    assert meta_pivot["impressions"] == 80_000
    assert meta_pivot["conversions"] == 25
    assert meta_pivot["revenue_eur"] == Decimal("3950.60")


def test_r5_the_restatement_carries_the_corrected_figures(mini_fixture: Path) -> None:
    restatement = read(mini_fixture, RESTATEMENT_KEY)

    assert restatement.num_rows == 1
    (row,) = restatement.to_pylist()
    assert row["account_id"] == PIVOT_ACCOUNT_ID
    assert row["campaign_id"] == PIVOT_CAMPAIGN_ID
    assert row["product_id"] == FLAGSHIP_PRODUCT_ID
    assert str(row["segments_date"]) == "2026-07-15"
    assert row["conversions"] == 47
    assert row["revenue_eur"] == Decimal("7250.00")
    assert row["cost_micros"] == 1_234_500_000


@pytest.mark.foundation
@needs_lake_credentials
def test_r4_the_objects_land_in_the_lake_under_the_partition_convention() -> None:
    subprocess.run(
        ["make", "fixture"],  # noqa: S607
        cwd=REPO_ROOT,
        check=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )

    listing = create_lake_client().list_objects_v2(Bucket=LAKE_BUCKET, Prefix="raw/")
    keys = {stored["Key"] for stored in listing.get("Contents", [])}

    assert GOOGLE_DAY_KEY in keys
    assert META_DAY_KEY in keys
    assert RESTATEMENT_KEY in keys
