#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${PROJECT_DIR}/docker-compose.prod.yml}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-${PROJECT_DIR}/db/migrations}"
USE_DOCKER="${USE_DOCKER:-true}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[[ -d "${MIGRATIONS_DIR}" ]] || fail "missing migrations directory: ${MIGRATIONS_DIR}"

cd "${PROJECT_DIR}"

if [[ "${USE_DOCKER}" == "true" ]]; then
  [[ -f "${COMPOSE_FILE}" ]] || fail "missing compose file: ${COMPOSE_FILE}"
  command -v docker >/dev/null 2>&1 || fail "docker is not installed or not available on PATH."

  docker compose -f "${COMPOSE_FILE}" up -d postgres
  docker compose -f "${COMPOSE_FILE}" run --rm --build --no-deps -T \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -v "${PROJECT_DIR}:/app:ro" \
    api \
    python -m api.db.migration_runner --migrations-dir /app/db/migrations "$@"
else
  if [[ -z "${PYTHON_BIN:-}" ]]; then
    if command -v python3 >/dev/null 2>&1; then
      PYTHON_BIN="python3"
    else
      PYTHON_BIN="python"
    fi
  fi
  "${PYTHON_BIN}" -m api.db.migration_runner --migrations-dir "${MIGRATIONS_DIR}" "$@"
fi
