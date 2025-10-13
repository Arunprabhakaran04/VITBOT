#!/usr/bin/env bash
# Applies a SQL file to the running docker-compose Postgres service.
# Usage: ./scripts/apply_sql_to_db.sh backend/migrations/006_vitbot_full_setup.sql

set -euo pipefail
SQL_FILE=${1:-}
COMPOSE_PROJECT_DIR=$(pwd)

if [[ -z "${SQL_FILE}" ]]; then
  echo "Usage: $0 path/to/sqlfile.sql"
  exit 2
fi

if [[ ! -f "${SQL_FILE}" ]]; then
  echo "SQL file not found: ${SQL_FILE}"
  exit 2
fi

echo "Applying ${SQL_FILE} to Postgres service 'db' (container: vitbot-db)"

docker compose exec -T db psql -U postgres -d VITBOT -f - <<EOF
$(cat ${SQL_FILE})
EOF

echo "Finished applying ${SQL_FILE}"