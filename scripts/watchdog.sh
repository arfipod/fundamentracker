#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
DEFAULT_HEALTH_URL="http://127.0.0.1:8000/health/ready"
DEFAULT_WATCHDOG_SERVICES="api"

log() {
  printf '[fundamentracker-watchdog] %s\n' "$*"
}

warn() {
  printf '[fundamentracker-watchdog] WARNING: %s\n' "$*" >&2
}

fail() {
  printf '[fundamentracker-watchdog] ERROR: %s\n' "$*" >&2
  exit 1
}

read_env_value() {
  local key="$1"
  local file="$2"
  local line value

  [[ -f "${file}" ]] || return 0

  line="$(
    awk -v key="${key}" '
      $0 ~ "^[[:space:]]*(export[[:space:]]+)?" key "=" {
        sub(/^[[:space:]]*export[[:space:]]+/, "", $0)
        sub(/^[[:space:]]*/, "", $0)
        print
      }
    ' "${file}" | tail -n 1
  )"

  [[ -n "${line}" ]] || return 0

  value="${line#*=}"
  value="${value%$'\r'}"

  if [[ "${value}" == \"*\" && "${value}" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "${value}" == \'*\' && "${value}" == *\' ]]; then
    value="${value:1:${#value}-2}"
  else
    value="${value%%#*}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
  fi

  printf '%s' "${value}"
}

health_url="${PUBLIC_HEALTH_URL:-$(read_env_value PUBLIC_HEALTH_URL "${ENV_FILE}")}"
health_url="${health_url:-${DEFAULT_HEALTH_URL}}"

wait_seconds="${WATCHDOG_RECHECK_WAIT_SECONDS:-$(read_env_value WATCHDOG_RECHECK_WAIT_SECONDS "${ENV_FILE}")}"
wait_seconds="${wait_seconds:-30}"

curl_timeout="${WATCHDOG_CURL_TIMEOUT_SECONDS:-$(read_env_value WATCHDOG_CURL_TIMEOUT_SECONDS "${ENV_FILE}")}"
curl_timeout="${curl_timeout:-10}"

api_auth_token="${API_AUTH_TOKEN:-$(read_env_value API_AUTH_TOKEN "${ENV_FILE}")}"

services_value="${WATCHDOG_SERVICES:-$(read_env_value WATCHDOG_SERVICES "${ENV_FILE}")}"
services_value="${services_value#"${services_value%%[![:space:]]*}"}"
services_value="${services_value%"${services_value##*[![:space:]]}"}"
services_value="${services_value:-${DEFAULT_WATCHDOG_SERVICES}}"
read -r -a SERVICES <<< "${services_value}"

[[ "${wait_seconds}" =~ ^[0-9]+$ ]] || fail "WATCHDOG_RECHECK_WAIT_SECONDS must be a non-negative integer."
[[ "${curl_timeout}" =~ ^[0-9]+$ ]] || fail "WATCHDOG_CURL_TIMEOUT_SECONDS must be a non-negative integer."
if [[ "${#SERVICES[@]}" -eq 0 ]]; then
  fail "WATCHDOG_SERVICES must list at least one Docker Compose service."
fi

for service in "${SERVICES[@]}"; do
  [[ "${service}" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || fail "invalid service in WATCHDOG_SERVICES: ${service}"
done

[[ -f "${COMPOSE_FILE}" ]] || fail "missing production compose file: ${COMPOSE_FILE}"
command -v docker >/dev/null 2>&1 || fail "docker is not installed or not available on PATH."
command -v curl >/dev/null 2>&1 || fail "curl is not installed or not available on PATH."

check_health() {
  local curl_args=(
    --fail
    --silent
    --show-error
    --max-time "${curl_timeout}"
  )

  if [[ -n "${api_auth_token}" ]]; then
    curl_args+=(--header "Authorization: Bearer ${api_auth_token}")
  fi

  curl "${curl_args[@]}" "${health_url}" >/dev/null
}

log "checking health URL: ${health_url}"
log "watchdog services: ${SERVICES[*]}"

if check_health; then
  log "health check passed."
  exit 0
fi

warn "health check failed; restarting services: ${SERVICES[*]}"
if ! docker compose -f "${COMPOSE_FILE}" restart "${SERVICES[@]}"; then
  warn "docker compose restart failed; continuing to recheck before force recreate."
fi

log "waiting ${wait_seconds}s before retrying health check."
sleep "${wait_seconds}"

if check_health; then
  log "health check passed after service restart."
  exit 0
fi

warn "health check still failing; force recreating services: ${SERVICES[*]}"
if ! docker compose -f "${COMPOSE_FILE}" up -d --force-recreate "${SERVICES[@]}"; then
  fail "docker compose force recreate failed."
fi

log "waiting ${wait_seconds}s before final health check."
sleep "${wait_seconds}"

if check_health; then
  log "health check passed after force recreate."
  exit 0
fi

fail "health check still failing after restart and force recreate."
