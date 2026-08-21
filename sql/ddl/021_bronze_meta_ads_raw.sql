-- The other ad network, with the other schema: spend in euros, no product column,
-- the report date under another name. Conforming the two is S-04's job, not Bronze's.
CREATE TABLE IF NOT EXISTS bronze.meta_ads_raw
(
    _source       LowCardinality(String),
    _source_file  String,
    _extracted_at Date,
    _ingested_at  DateTime,
    account_id    String,
    campaign_id   String,
    date_start    Date32,
    spend         Decimal(18, 2),
    clicks        Int64,
    impressions   Int64,
    conversions   Int64,
    revenue_eur   Decimal(18, 2)
)
ENGINE = MergeTree
PARTITION BY (_source, _extracted_at)
ORDER BY (account_id, date_start, campaign_id);
