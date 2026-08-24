#!/usr/bin/env bash
# Re-downloading a day already ingested never changes the number of rows, only their
# values: the ad network revises its figures, the pipeline replaces them instead of
# stacking a second version on top.
set -euo pipefail

DAILY_EXTRACTION_DAYS=(2026-07-15 2026-07-16 2026-07-17)
RESTATEMENT_EXTRACTION_DAY=2026-08-20
SOURCES=(google_ads meta_ads)
LOADED_TABLES=(bronze.google_ads_raw bronze.meta_ads_raw silver.ads_daily gold.campaign_daily)

SILVER_ROW_COUNT=3030
FLAGSHIP_PRODUCT_ID=sku_77
INITIAL_CONVERSIONS=40
INITIAL_ROW_REVENUE_EUR=6172.500000
RESTATED_CONVERSIONS=47
RESTATED_ROW_REVENUE_EUR=7250.000000

PIVOT_CAMPAIGN_DAY="source = 'google_ads' AND account_id = 'acct_01'
                    AND campaign_id = 'camp_003' AND report_date = '2026-07-15'"
PIVOT_CAMPAIGN_LABEL="google_ads acct_01 camp_003 2026-07-15"
INITIAL_SPEND_EUR=12345.000000
INITIAL_REVENUE_EUR=61725.000000
INITIAL_CAMPAIGN_CONVERSIONS=400
ROAS_DECIMALS=4
INITIAL_ROAS=5.0000
RESTATED_REVENUE_EUR=62802.500000
RESTATED_CAMPAIGN_CONVERSIONS=407
RESTATED_ROAS=5.0873

# Trailing zeros are kept so a decimal reads with the scale its column declares: an amount
# compared as 12345.000000 says out loud that it is exact to the micro-euro.
query_clickhouse() {
	docker compose exec -T clickhouse clickhouse-client \
		--output_format_decimal_trailing_zeros 1 "$@"
}

check() {
	local label=$1 expected=$2 actual=$3
	if [ "$actual" != "$expected" ]; then
		echo "$label: $actual instead of $expected" >&2
		exit 1
	fi
}

silver() {
	local expression=$1 predicate=${2:-1}
	query_clickhouse --query "SELECT $expression FROM silver.ads_daily FINAL WHERE $predicate"
}

flagship_row() {
	silver "$1" "$PIVOT_CAMPAIGN_DAY AND product_id = '$FLAGSHIP_PRODUCT_ID'"
}

pivot_aggregate() {
	query_clickhouse --query "SELECT $1 FROM gold.campaign_daily WHERE $PIVOT_CAMPAIGN_DAY"
}

# ROAS is a ratio of sums, read at query time — Gold stores the components only.
pivot_roas() {
	pivot_aggregate "toDecimal64(round(revenue_eur / spend_eur, $ROAS_DECIMALS), $ROAS_DECIMALS)"
}

# A scenario that only asserts asks to be believed; printing both states lets the reader
# see the restatement land on the figures it revises.
report_state() {
	local label=$1
	echo "  --- $label"
	echo "  silver  rows=$(silver "count()")" \
		"| $FLAGSHIP_PRODUCT_ID conversions=$(flagship_row "conversions")" \
		"revenue_eur=$(flagship_row "revenue_eur")"
	echo "  gold    $PIVOT_CAMPAIGN_LABEL" \
		"| spend_eur=$(pivot_aggregate "spend_eur")" \
		"revenue_eur=$(pivot_aggregate "revenue_eur")" \
		"conversions=$(pivot_aggregate "conversions")" \
		"roas=$(pivot_roas)"
}

publish_layers() {
	make --no-print-directory silver >/dev/null
	make --no-print-directory gold >/dev/null
}

ingest_restatement() {
	scripts/ingest-extraction.sh google_ads "$RESTATEMENT_EXTRACTION_DAY" >/dev/null
	publish_layers
}

make --no-print-directory fixture >/dev/null
for table in "${LOADED_TABLES[@]}"; do
	query_clickhouse --query "TRUNCATE TABLE $table"
done
for source in "${SOURCES[@]}"; do
	for extraction_day in "${DAILY_EXTRACTION_DAYS[@]}"; do
		scripts/ingest-extraction.sh "$source" "$extraction_day" >/dev/null
	done
done
publish_layers

report_state "before the restatement"

check "before the restatement · one row per business key" "$SILVER_ROW_COUNT" "$(silver "count()")"
check "before the restatement · conversions of the flagship row" "$INITIAL_CONVERSIONS" \
	"$(flagship_row "conversions")"
check "before the restatement · revenue of the flagship row" "$INITIAL_ROW_REVENUE_EUR" \
	"$(flagship_row "revenue_eur")"
check "before the restatement · aggregated revenue" "$INITIAL_REVENUE_EUR" \
	"$(pivot_aggregate "revenue_eur")"
check "before the restatement · aggregated conversions" "$INITIAL_CAMPAIGN_CONVERSIONS" \
	"$(pivot_aggregate "conversions")"
check "before the restatement · ROAS" "$INITIAL_ROAS" \
	"$(pivot_roas)"

ingest_restatement
report_state "after the restatement of $RESTATEMENT_EXTRACTION_DAY"

check "R1 · the row count is unchanged" "$SILVER_ROW_COUNT" "$(silver "count()")"
check "R1 · the restated conversions win" "$RESTATED_CONVERSIONS" "$(flagship_row "conversions")"
check "R1 · the restated revenue wins" "$RESTATED_ROW_REVENUE_EUR" "$(flagship_row "revenue_eur")"

check "R2 · Gold revenue reflects the restatement" "$RESTATED_REVENUE_EUR" \
	"$(pivot_aggregate "revenue_eur")"
check "R2 · Gold conversions reflect the restatement" "$RESTATED_CAMPAIGN_CONVERSIONS" \
	"$(pivot_aggregate "conversions")"
check "R2 · the ROAS follows" "$RESTATED_ROAS" \
	"$(pivot_roas)"
check "R2 · the spend was not revised" "$INITIAL_SPEND_EUR" "$(pivot_aggregate "spend_eur")"

silver_totals=$(silver "count(), sum(spend_eur), sum(conversions)")
gold_totals=$(query_clickhouse --query "SELECT count(), sum(spend_eur), sum(conversions)
                                        FROM gold.campaign_daily")
ingest_restatement
ingest_restatement

check "R3 · Silver is untouched by the replays" "$silver_totals" \
	"$(silver "count(), sum(spend_eur), sum(conversions)")"
check "R3 · Gold is untouched by the replays" "$gold_totals" \
	"$(query_clickhouse --query "SELECT count(), sum(spend_eur), sum(conversions)
	                             FROM gold.campaign_daily")"

echo "S-05 · a late restatement replaces the figures instead of adding to them: ok"
