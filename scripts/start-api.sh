#!/usr/bin/env sh
set -eu

if [ "${RUN_MIGRATIONS_ON_START:-false}" = "true" ]; then
  python -m api.db.migration_runner
fi

exec uvicorn api.api:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
