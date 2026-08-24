-- Gold and Silver agree to the cent, month by month. The comparison is restricted to the
-- months Gold publishes: a month conformed in Silver but not yet rebuilt is a publication
-- that has not happened, not a disagreement. A non-zero gap names its partition.
SELECT
    report_month,
    sumIf(spend_eur, layer = 'gold') - sumIf(spend_eur, layer = 'silver')     AS spend_eur_gap,
    sumIf(clicks, layer = 'gold') - sumIf(clicks, layer = 'silver')           AS clicks_gap,
    sumIf(impressions, layer = 'gold') - sumIf(impressions, layer = 'silver') AS impressions_gap,
    sumIf(conversions, layer = 'gold') - sumIf(conversions, layer = 'silver') AS conversions_gap,
    sumIf(revenue_eur, layer = 'gold') - sumIf(revenue_eur, layer = 'silver') AS revenue_eur_gap
FROM
(
    SELECT
        'gold'                AS layer,
        toYYYYMM(report_date) AS report_month,
        spend_eur,
        clicks,
        impressions,
        conversions,
        revenue_eur
    FROM gold.{gold_table:Identifier}

    UNION ALL

    SELECT
        'silver',
        toYYYYMM(report_date),
        spend_eur,
        clicks,
        impressions,
        conversions,
        revenue_eur
    FROM silver.ads_daily FINAL
    WHERE toYYYYMM(report_date) IN (
        SELECT DISTINCT toYYYYMM(report_date) FROM gold.{gold_table:Identifier}
    )
)
GROUP BY report_month
HAVING spend_eur_gap != 0
    OR clicks_gap != 0
    OR impressions_gap != 0
    OR conversions_gap != 0
    OR revenue_eur_gap != 0
ORDER BY report_month;
