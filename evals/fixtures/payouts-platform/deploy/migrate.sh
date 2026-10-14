#!/usr/bin/env bash
set -euo pipefail
# Applies pending migrations in order. Each file runs in its own transaction.
for f in db/migrations/*.sql; do
  version=$(basename "$f" .sql)
  if ! psql "$DATABASE_URL" -tAc "SELECT 1 FROM schema_migrations WHERE version = '$version'" | grep -q 1; then
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 --single-transaction -f "$f"
    psql "$DATABASE_URL" -c "INSERT INTO schema_migrations (version) VALUES ('$version')"
  fi
done
