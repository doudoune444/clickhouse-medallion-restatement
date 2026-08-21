#!/usr/bin/env bash
# Reloading an extraction leaves Bronze in the state it would have had after a single
# load — without losing the neighbouring objects.
set -euo pipefail

SINGLE_OBJECT_EXTRACTION=2026-07-16
TWO_OBJECT_EXTRACTION=2026-07-17
ROWS_PER_GOOGLE_OBJECT=1000
ROWS_PER_META_OBJECT=10
PIVOT_COST_MICROS=1234500000
PIVOT_SOURCE_FILE="s3://lake/raw/source=google_ads/report=campaign_daily/extracted_at=$SINGLE_OBJECT_EXTRACTION/part-0001.parquet"
TWO_OBJECT_EXTRACTION_URL="http://minio:10000/lake/raw/source=google_ads/report=campaign_daily/extracted_at=$TWO_OBJECT_EXTRACTION"

query_clickhouse() { docker compose exec -T clickhouse clickhouse-client "$@"; }

check() {
	local label=$1 expected=$2 actual=$3
	if [ "$actual" != "$expected" ]; then
		echo "$label: $actual instead of $expected" >&2
		exit 1
	fi
}

google_partition() {
	query_clickhouse --query "SELECT $1 FROM bronze.google_ads_raw WHERE _extracted_at = '$2'"
}

# The fixture ships one object per extraction; R3 needs an extraction holding two.
make --no-print-directory fixture >/dev/null
query_clickhouse --query "INSERT INTO FUNCTION s3('$TWO_OBJECT_EXTRACTION_URL/part-0002.parquet', 'Parquet')
                          SELECT * FROM s3('$TWO_OBJECT_EXTRACTION_URL/part-0001.parquet', 'Parquet')
                          SETTINGS s3_truncate_on_insert = 1"

scripts/ingest-extraction.sh google_ads "$SINGLE_OBJECT_EXTRACTION" >/dev/null
scripts/ingest-extraction.sh meta_ads "$SINGLE_OBJECT_EXTRACTION" >/dev/null

check "R1 · rows of one object" "$ROWS_PER_GOOGLE_OBJECT" \
	"$(google_partition "count()" "$SINGLE_OBJECT_EXTRACTION")"
check "R1 · cost_micros stays an integer" "Int64" \
	"$(query_clickhouse --query "SELECT type FROM system.columns
	                             WHERE database = 'bronze' AND table = 'google_ads_raw'
	                               AND name = 'cost_micros'")"
check "R1 · no conversion to euros" "$PIVOT_COST_MICROS" \
	"$(query_clickhouse --query "SELECT cost_micros FROM bronze.google_ads_raw
	                             WHERE account_id = 'acct_01' AND campaign_id = 'camp_003'
	                               AND product_id = 'sku_77' AND segments_date = '2026-07-15'")"
check "R1 · the other source keeps its own schema" "$ROWS_PER_META_OBJECT" \
	"$(query_clickhouse --query "SELECT count() FROM bronze.meta_ads_raw
	                             WHERE _extracted_at = '$SINGLE_OBJECT_EXTRACTION'")"

check "R2 · traceability of every row" "1" \
	"$(google_partition "count() = countIf(_source = 'google_ads'
	                                       AND _source_file = '$PIVOT_SOURCE_FILE'
	                                       AND _extracted_at = '$SINGLE_OBJECT_EXTRACTION'
	                                       AND _ingested_at > 0)" "$SINGLE_OBJECT_EXTRACTION")"

scripts/ingest-extraction.sh google_ads "$TWO_OBJECT_EXTRACTION" >/dev/null
check "R3 · both objects of the extraction are read" "2" \
	"$(google_partition "countDistinct(_source_file)" "$TWO_OBJECT_EXTRACTION")"
check "R3 · the extraction is rebuilt whole" "$((2 * ROWS_PER_GOOGLE_OBJECT))" \
	"$(google_partition "count()" "$TWO_OBJECT_EXTRACTION")"
check "R3 · the neighbouring extraction is untouched" "$ROWS_PER_GOOGLE_OBJECT" \
	"$(google_partition "count()" "$SINGLE_OBJECT_EXTRACTION")"

scripts/ingest-extraction.sh google_ads "$SINGLE_OBJECT_EXTRACTION" >/dev/null
scripts/ingest-extraction.sh google_ads "$SINGLE_OBJECT_EXTRACTION" >/dev/null
check "R4 · reloading twice changes nothing" "$ROWS_PER_GOOGLE_OBJECT" \
	"$(google_partition "count()" "$SINGLE_OBJECT_EXTRACTION")"
check "R4 · one single ingestion instant remains" "1" \
	"$(google_partition "countDistinct(_ingested_at)" "$SINGLE_OBJECT_EXTRACTION")"

echo "S-03 · S3 extraction -> Bronze, reloadable without losing a neighbour: ok"
