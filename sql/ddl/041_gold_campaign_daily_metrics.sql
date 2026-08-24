-- The derived metrics of Gold, computed at read time from the components the table stores.
-- Each one is a ratio of sums, never a mean of ratios: the sums come from the row, so a
-- campaign-day and a whole month go through the same formula. A zero denominator yields
-- NULL — an unknown ratio says so, where 0 or inf would be read as a measurement.
CREATE OR REPLACE VIEW gold.campaign_daily_metrics AS
SELECT
    source,
    account_id,
    campaign_id,
    report_date,
    spend_eur,
    clicks,
    impressions,
    conversions,
    revenue_eur,
    toDecimal64(round(revenue_eur / nullIf(spend_eur, 0), 4), 4)     AS roas,
    spend_eur / nullIf(conversions, 0)                              AS cpa,
    CAST(clicks AS Decimal(18, 6)) / nullIf(impressions, 0)         AS ctr,
    spend_eur / nullIf(clicks, 0)                                   AS cpc
FROM gold.campaign_daily;
