#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${PROJECT_DIR}/docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-/srv/fundamentracker/backups}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[[ -f "${COMPOSE_FILE}" ]] || fail "missing production compose file: ${COMPOSE_FILE}"
command -v docker >/dev/null 2>&1 || fail "docker is not installed or not available on PATH."

mkdir -p "${BACKUP_DIR}"

backup_path="${BACKUP_DIR}/fundamentracker-$(date +%Y%m%d-%H%M%S).dump"

cd "${PROJECT_DIR}"
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "${backup_path}"

printf 'Wrote database backup: %s\n' "${backup_path}"
