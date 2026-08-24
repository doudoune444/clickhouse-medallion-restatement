-- `meta_ads` reports its spend in euros, under another name, and publishes no product
-- breakdown at all. The missing dimension becomes an explicit sentinel, never a NULL:
-- a campaign-day of Meta is a real measurement, only its product is unknown.
INSERT INTO silver.ads_daily
SELECT
    'meta_ads'          AS source,
    account_id,
    toDate(date_start)  AS report_date,
    campaign_id,
    '__unknown__'       AS product_id,
    spend               AS spend_eur,
    clicks,
    impressions,
    conversions,
    revenue_eur,
    _extracted_at
FROM bronze.meta_ads_raw;
