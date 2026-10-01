#!/usr/bin/env bash
# Generates traffic so the Grafana panels (rate, latency, errors) have data.
#   bash scripts/load-test.sh [base_url] [requests]
set -uo pipefail

BASE_URL=${1:-http://localhost:8080}
REQUESTS=${2:-500}

for i in $(seq 1 "$REQUESTS"); do
  curl -s -o /dev/null "$BASE_URL/api/v1/sample"
  curl -s -o /dev/null -X POST "$BASE_URL/api/v1/liquidity" -H "Content-Type: application/json" \
    -d "{\"current_assets\": $((RANDOM % 500 + 50)), \"current_liabilities\": $((RANDOM % 300 + 50))}"
  curl -s -o /dev/null -X POST "$BASE_URL/api/v1/solvency" -H "Content-Type: application/json" \
    -d "{\"total_debt\": $((RANDOM % 400)), \"total_equity\": $((RANDOM % 200 + 20))}"
  # Every 10th request sends invalid input to produce some 4xx responses
  if (( i % 10 == 0 )); then
    curl -s -o /dev/null -X POST "$BASE_URL/api/v1/analyze" -H "Content-Type: application/json" -d '"bad"'
  fi
  (( i % 50 == 0 )) && echo "sent $i rounds"
done
echo "done"
