-- `google_ads` reports its spend in micro-euros and breaks it down by product.
-- 1 000 000 micros make one euro; the division stays decimal so no cent is rounded away.
INSERT INTO silver.ads_daily
SELECT
    'google_ads'                            AS source,
    account_id,
    toDate(segments_date)                   AS report_date,
    campaign_id,
    product_id,
    toDecimal128(cost_micros, 6) / 1000000  AS spend_eur,
    clicks,
    impressions,
    conversions,
    revenue_eur,
    _extracted_at
FROM bronze.google_ads_raw;
