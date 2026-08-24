#!/usr/bin/env bash
# A contract answers with the rows that violate it: an empty answer is a pass. The exit
# code is what callers act on — the rebuild of Gold runs this against its staging table
# and refuses to swap the partition in when it comes back non-zero.
set -euo pipefail

CONTRACT_DIRECTORY=sql/contracts
DEFAULT_GOLD_TABLE=campaign_daily

gold_table=${1:-$DEFAULT_GOLD_TABLE}

query_clickhouse() { docker compose exec -T clickhouse clickhouse-client "$@"; }

violated=0
for contract_file in "$CONTRACT_DIRECTORY"/*.sql; do
	contract_name=$(basename "$contract_file" .sql)
	violations=$(query_clickhouse \
		--param_gold_table "$gold_table" \
		--queries-file "/$contract_file")
	if [ -n "$violations" ]; then
		echo "  contract  FAILED  $contract_name  (gold.$gold_table)"
		echo "$violations" | sed 's/^/            /'
		violated=1
	else
		echo "  contract  ok      $contract_name  (gold.$gold_table)"
	fi
done

exit $violated
