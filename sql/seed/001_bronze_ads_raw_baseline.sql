-- Deterministic by construction: no value reads the system clock, otherwise
-- `sum(cityHash64(*))` would differ from one rebuild to the next.
TRUNCATE TABLE bronze.ads_raw;

INSERT INTO bronze.ads_raw
SELECT
    'google_ads' AS _source,
    's3://lake/raw/source=google_ads/report=campaign_daily/extracted_at=2026-07-17/part-0001.parquet'
        AS _source_file,
    toDate('2026-07-17') AS _extracted_at,
    toDateTime('2026-07-17 03:00:00') AS _ingested_at,
    ['acct_01', 'acct_02'][number % 2 + 1] AS account_id,
    concat('camp_', leftPad(toString(intDiv(number, 2) % 5 + 1), 3, '0')) AS campaign_id,
    toDate('2026-07-14') + toIntervalDay(intDiv(number, 10)) AS report_date,
    toInt64(1000000 * (number + 1)) AS cost_micros,
    toUInt32(10 * number) AS clicks,
    toUInt64(1000 * number) AS impressions,
    toUInt32(number) AS conversions
FROM numbers(30);
