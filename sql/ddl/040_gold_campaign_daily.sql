-- Gold: the campaign-day aggregate read by the consumers. It stores the components of the
-- business metrics, never their ratios, and is rebuilt month by month from silver … FINAL.
CREATE TABLE IF NOT EXISTS gold.campaign_daily
(
    source      LowCardinality(String),
    account_id  LowCardinality(String),
    campaign_id LowCardinality(String),
    report_date Date CODEC(Delta, ZSTD),
    spend_eur   Decimal(18, 6),
    clicks      Int64 CODEC(Delta, ZSTD),
    impressions Int64 CODEC(Delta, ZSTD),
    conversions Int64 CODEC(Delta, ZSTD),
    revenue_eur Decimal(18, 6)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(report_date)
ORDER BY (source, account_id, campaign_id, report_date);
