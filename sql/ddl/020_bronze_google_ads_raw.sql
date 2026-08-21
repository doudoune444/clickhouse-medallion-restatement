-- Bronze keeps the physical types of the Parquet file: micros stay integers,
-- dates stay date32, amounts stay exact decimals. No business rule lives here.
CREATE TABLE IF NOT EXISTS bronze.google_ads_raw
(
    _source       LowCardinality(String),
    _source_file  String,
    _extracted_at Date,
    _ingested_at  DateTime,
    account_id    String,
    campaign_id   String,
    product_id    String,
    segments_date Date32,
    cost_micros   Int64,
    clicks        Int64,
    impressions   Int64,
    conversions   Int64,
    revenue_eur   Decimal(18, 2)
)
ENGINE = MergeTree
PARTITION BY (_source, _extracted_at)
ORDER BY (account_id, segments_date, campaign_id, product_id);
