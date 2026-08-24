-- Each layer holds one row per grain. Silver is read with `FINAL`, which is how its
-- consumers read it: a restated row that has not been merged yet is a version, not a
-- duplicate. Gold is a plain MergeTree rebuilt by partition swap, so a duplicate grain
-- there is a real one — and the shape a silent double count takes.
SELECT
    layer,
    report_month,
    duplicate_rows
FROM
(
    SELECT
        'silver'                    AS layer,
        toYYYYMM(report_date)       AS report_month,
        count() - countDistinct(source, account_id, report_date, campaign_id, product_id)
                                    AS duplicate_rows
    FROM silver.ads_daily FINAL
    GROUP BY report_month

    UNION ALL

    SELECT
        'gold'                      AS layer,
        toYYYYMM(report_date)       AS report_month,
        count() - countDistinct(source, account_id, campaign_id, report_date)
                                    AS duplicate_rows
    FROM gold.{gold_table:Identifier}
    GROUP BY report_month
)
WHERE duplicate_rows != 0
ORDER BY layer, report_month;
