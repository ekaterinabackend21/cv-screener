#!/bin/sh
set -eu

ES_URL="${ELASTICSEARCH_URL:-http://elasticsearch:9200}"
INDEX="${ELASTICSEARCH_INDEX:-cv_candidates}"

if curl -fsS "${ES_URL}/${INDEX}" >/dev/null 2>&1; then
  echo "Elasticsearch index '${INDEX}' already exists."
  exit 0
fi

curl -fsS -X PUT "${ES_URL}/${INDEX}" \
  -H 'Content-Type: application/json' \
  --data-binary @/config/index_mapping.json
echo
echo "Created Elasticsearch index '${INDEX}'."
