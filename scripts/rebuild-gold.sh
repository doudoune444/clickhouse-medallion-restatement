#!/usr/bin/env bash
# Gold is rebuilt one month at a time and swapped in: an incremental materialized view
# would fire on the INSERT of a restated row and aggregate it on top of the row it
# revises, which is a silent double count.
set -euo pipefail

GOLD_TABLE=gold.campaign_daily
STAGING_TABLE=campaign_daily_staging
AGGREGATION_FILE=/sql/aggregate/campaign_daily.sql

query_clickhouse() { docker compose exec -T clickhouse clickhouse-client "$@"; }

report_months=$(query_clickhouse --query "SELECT DISTINCT toYYYYMM(report_date)
                                          FROM silver.ads_daily ORDER BY 1")

for report_month in $report_months; do
	query_clickhouse --query "CREATE TABLE IF NOT EXISTS gold.$STAGING_TABLE AS $GOLD_TABLE"
	query_clickhouse --query "TRUNCATE TABLE gold.$STAGING_TABLE"
	query_clickhouse \
		--param_staging_table "$STAGING_TABLE" \
		--param_report_month "$report_month" \
		--queries-file "$AGGREGATION_FILE"
	query_clickhouse --query "ALTER TABLE $GOLD_TABLE
	                          REPLACE PARTITION ID '$report_month'
	                          FROM gold.$STAGING_TABLE"
	query_clickhouse --query "DROP TABLE gold.$STAGING_TABLE"
	echo "  gold  report_month=$report_month"
done
