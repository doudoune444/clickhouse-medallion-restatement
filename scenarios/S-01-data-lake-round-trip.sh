#!/usr/bin/env bash
# The foundation is "ready to use" once ClickHouse really writes to and reads back from the lake.
set -euo pipefail

ROUND_TRIP_TABLE=default.data_lake_round_trip_witness
ROUND_TRIP_ROW_COUNT=1000
EXPECTED_SUM=499500

query_clickhouse() { docker compose exec -T clickhouse clickhouse-client "$@"; }

disks_named_data_lake=$(query_clickhouse --query "SELECT count() FROM system.disks WHERE name = 'data_lake'")
if [ "$disks_named_data_lake" != "1" ]; then
	echo "the 'data_lake' disk is not declared (count = $disks_named_data_lake)" >&2
	exit 1
fi

query_clickhouse --query "DROP TABLE IF EXISTS $ROUND_TRIP_TABLE"
query_clickhouse --query "CREATE TABLE $ROUND_TRIP_TABLE (n UInt32) ENGINE = MergeTree ORDER BY n
                          SETTINGS storage_policy = 'store_on_data_lake'"
query_clickhouse --query "INSERT INTO $ROUND_TRIP_TABLE SELECT number FROM numbers($ROUND_TRIP_ROW_COUNT)"
sum_read_back=$(query_clickhouse --query "SELECT sum(n) FROM $ROUND_TRIP_TABLE")
query_clickhouse --query "DROP TABLE $ROUND_TRIP_TABLE"

if [ "$sum_read_back" != "$EXPECTED_SUM" ]; then
	echo "data lake round trip is wrong: $sum_read_back instead of $EXPECTED_SUM" >&2
	exit 1
fi

echo "S-01 · ClickHouse -> MinIO data lake round trip: ok"
