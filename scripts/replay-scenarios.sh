#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

scenarios=(scenarios/*.sh)

if [ ${#scenarios[@]} -eq 0 ]; then
	echo "no scenario to replay"
	exit 0
fi

for scenario in "${scenarios[@]}"; do
	echo "== $scenario"
	bash "$scenario"
done
