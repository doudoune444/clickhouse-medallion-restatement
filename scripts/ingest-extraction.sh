#!/usr/bin/env bash
# The unit of reload is the whole extraction: every object it holds is read into a
# staging table, and the partition is swapped in only once that rebuild succeeded.
set -euo pipefail

source_name=${1:?usage: ingest-extraction.sh <source> <extracted_at>}
extraction_day=${2:?usage: ingest-extraction.sh <source> <extracted_at>}

LAKE_URL=http://minio:10000/lake
RAW_PREFIX=raw
CAMPAIGN_DAILY_REPORT=campaign_daily

bronze_table=bronze.${source_name}_raw
staging_table=${source_name}_raw_staging
projection_file=/sql/ingest/${source_name}.sql
extraction_url=$LAKE_URL/$RAW_PREFIX/source=$source_name/report=$CAMPAIGN_DAILY_REPORT/extracted_at=$extraction_day/*.parquet

query_clickhouse() { docker compose exec -T clickhouse clickhouse-client "$@"; }

query_clickhouse --query "CREATE TABLE IF NOT EXISTS bronze.$staging_table AS $bronze_table"
query_clickhouse --query "TRUNCATE TABLE bronze.$staging_table"
query_clickhouse \
	--param_staging_table "$staging_table" \
	--param_extracted_at "$extraction_day" \
	--param_extraction_url "$extraction_url" \
	--queries-file "$projection_file"
query_clickhouse --query "ALTER TABLE $bronze_table
                          REPLACE PARTITION ('$source_name', '$extraction_day')
                          FROM bronze.$staging_table"
query_clickhouse --query "DROP TABLE bronze.$staging_table"

echo "  ingest  $source_name extracted_at=$extraction_day"
