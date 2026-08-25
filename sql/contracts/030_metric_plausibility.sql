-- A click is a click on an impression, so a campaign-day can never report more of the
-- former than of the latter. The rule is exact: a tolerance would have to be justified,
-- and nothing justifies serving a figure this rule rejects.
SELECT
    'clicks <= impressions' AS rule,
    layer,
    report_month,
    count()                 AS violating_rows
FROM
(
    SELECT
        'silver'                AS layer,
        toYYYYMM(report_date)   AS report_month,
        clicks,
        impressions
    FROM silver.ads_daily FINAL

    UNION ALL

    SELECT
        'gold',
        toYYYYMM(report_date),
        clicks,
        impressions
    FROM gold.{gold_table:Identifier}
)
WHERE clicks > impressions
GROUP BY layer, report_month
ORDER BY layer, report_month;
