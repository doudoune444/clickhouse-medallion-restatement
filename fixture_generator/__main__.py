"""`make fixture`: write `fixtures/mini` on disk, then publish it to the lake."""

from __future__ import annotations

import argparse
from pathlib import Path

from fixture_generator.mini_fixture import (
    DEFAULT_DESTINATION,
    DEFAULT_SEED,
    write_mini_fixture,
)
from fixture_generator.object_storage import LAKE_BUCKET, RAW_PREFIX, create_lake_client, upload


def main() -> None:
    """Generate the fixture and upload it, reporting what landed where."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    arguments = parser.parse_args()

    object_keys = write_mini_fixture(arguments.destination, arguments.seed)
    upload(create_lake_client(), arguments.destination, object_keys)
    print(f"  fixture  {len(object_keys)} objects in s3://{LAKE_BUCKET}/{RAW_PREFIX}/")


if __name__ == "__main__":
    main()
