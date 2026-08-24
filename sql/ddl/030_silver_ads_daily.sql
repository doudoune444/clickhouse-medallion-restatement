-- Silver: the single typed model both ad networks are conformed to. One row per business
-- key, the most recently extracted one winning — that is what absorbs a late restatement.
CREATE TABLE IF NOT EXISTS silver.ads_daily
(
    source        LowCardinality(String),
    account_id    LowCardinality(String),
    report_date   Date CODEC(Delta, ZSTD),
    campaign_id   LowCardinality(String),
    product_id    LowCardinality(String),
    spend_eur     Decimal(18, 6),
    clicks        Int64 CODEC(Delta, ZSTD),
    impressions   Int64 CODEC(Delta, ZSTD),
    conversions   Int64 CODEC(Delta, ZSTD),
    revenue_eur   Decimal(18, 6),
    _extracted_at Date CODEC(Delta, ZSTD)
)
ENGINE = ReplacingMergeTree(_extracted_at)
PARTITION BY toYYYYMM(report_date)
ORDER BY (source, account_id, report_date, campaign_id, product_id);
