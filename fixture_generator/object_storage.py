"""Where an extraction lands in the lake, and how it gets there."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import boto3

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date
    from pathlib import Path

    from mypy_boto3_s3.client import S3Client

LAKE_BUCKET = "lake"
RAW_PREFIX = "raw"
CAMPAIGN_DAILY_REPORT = "campaign_daily"

DEFAULT_LAKE_ENDPOINT_URL = "http://127.0.0.1:10000"
LAKE_REGION = "us-east-1"


def report_object_key(source_name: str, extraction_day: date, file_name: str) -> str:
    """Return the lake key of one object of one extraction."""
    return (
        f"{RAW_PREFIX}/source={source_name}/report={CAMPAIGN_DAILY_REPORT}"
        f"/extracted_at={extraction_day:%Y-%m-%d}/{file_name}"
    )


def create_lake_client() -> S3Client:
    """Return a client on the lake, credentials taken from the environment."""
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("LAKE_ENDPOINT_URL", DEFAULT_LAKE_ENDPOINT_URL),
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        region_name=LAKE_REGION,
    )


def upload(client: S3Client, source_directory: Path, object_keys: Iterable[str]) -> None:
    """Upload each object of `source_directory` to the key it is already stored under."""
    for object_key in object_keys:
        client.upload_file(str(source_directory / object_key), LAKE_BUCKET, object_key)
