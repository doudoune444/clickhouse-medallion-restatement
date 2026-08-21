"""Writing settings are pinned: the same seed must produce the same bytes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pyarrow.parquet as pq

if TYPE_CHECKING:
    from pathlib import Path

    import pyarrow as pa

PARQUET_VERSION: Literal["2.6"] = "2.6"
PARQUET_COMPRESSION: Literal["zstd"] = "zstd"
PARQUET_COMPRESSION_LEVEL = 3
ROWS_PER_ROW_GROUP = 100_000


def write_report(table: pa.Table, path: Path) -> None:
    """Write `table` to `path`, creating the partition directories on the way."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        table,
        path,
        version=PARQUET_VERSION,
        compression=PARQUET_COMPRESSION,
        compression_level=PARQUET_COMPRESSION_LEVEL,
        row_group_size=ROWS_PER_ROW_GROUP,
    )
