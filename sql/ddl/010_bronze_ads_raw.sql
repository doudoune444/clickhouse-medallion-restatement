-- Reproducibility baseline of the foundation: this is the table whose checksums
-- `make seed` pins down. The real Bronze tables, one per ad network, land with S-03.
CREATE TABLE IF NOT EXISTS bronze.ads_raw
(
    _source       LowCardinality(String),
    _source_file  String,
    _extracted_at Date,
    _ingested_at  DateTime,
    account_id    LowCardinality(String),
    campaign_id   LowCardinality(String),
    report_date   Date,
    cost_micros   Int64,
    clicks        UInt32,
    impressions   UInt64,
    conversions   UInt32
)
ENGINE = MergeTree
PARTITION BY (_source, _extracted_at)
ORDER BY (_source, _extracted_at, account_id, report_date, campaign_id);
