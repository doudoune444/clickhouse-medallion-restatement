-- One month of Gold, rebuilt from scratch. `FINAL` is what makes a restated row replace
-- the row it revises instead of being summed on top of it.
INSERT INTO gold.{staging_table:Identifier}
SELECT
    source,
    account_id,
    campaign_id,
    report_date,
    CAST(sum(spend_eur) AS Decimal(18, 6))   AS spend_eur,
    sum(clicks)                              AS clicks,
    sum(impressions)                         AS impressions,
    sum(conversions)                         AS conversions,
    CAST(sum(revenue_eur) AS Decimal(18, 6)) AS revenue_eur
FROM silver.ads_daily FINAL
WHERE toYYYYMM(report_date) = {report_month:UInt32}
GROUP BY source, account_id, campaign_id, report_date;
