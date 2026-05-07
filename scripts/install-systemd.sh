#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="fundamentracker.service"
WATCHDOG_SERVICE_NAME="fundamentracker-watchdog.service"
WATCHDOG_TIMER_NAME="fundamentracker-watchdog.timer"
SYSTEMD_DIR="/etc/systemd/system"
PROJECT_DIR="/opt/fundamentracker"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_SRC="${REPO_ROOT}/systemd/${SERVICE_NAME}"
SERVICE_DEST="${SYSTEMD_DIR}/${SERVICE_NAME}"
WATCHDOG_SERVICE_SRC="${REPO_ROOT}/systemd/${WATCHDOG_SERVICE_NAME}"
WATCHDOG_SERVICE_DEST="${SYSTEMD_DIR}/${WATCHDOG_SERVICE_NAME}"
WATCHDOG_TIMER_SRC="${REPO_ROOT}/systemd/${WATCHDOG_TIMER_NAME}"
WATCHDOG_TIMER_DEST="${SYSTEMD_DIR}/${WATCHDOG_TIMER_NAME}"
WATCHDOG_SCRIPT="${PROJECT_DIR}/scripts/watchdog.sh"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

if [[ "${EUID}" -ne 0 ]]; then
  fail "this installer must be run with sudo or as root."
fi

[[ -f "${SERVICE_SRC}" ]] || fail "missing service file: ${SERVICE_SRC}"
[[ -f "${WATCHDOG_SERVICE_SRC}" ]] || fail "missing watchdog service file: ${WATCHDOG_SERVICE_SRC}"
[[ -f "${WATCHDOG_TIMER_SRC}" ]] || fail "missing watchdog timer file: ${WATCHDOG_TIMER_SRC}"
[[ -d "${PROJECT_DIR}" ]] || fail "project directory does not exist: ${PROJECT_DIR}"
[[ -f "${PROJECT_DIR}/docker-compose.prod.yml" ]] || fail "missing production compose file: ${PROJECT_DIR}/docker-compose.prod.yml"
[[ -x "${WATCHDOG_SCRIPT}" ]] || fail "watchdog script is missing or not executable: ${WATCHDOG_SCRIPT}"
command -v docker >/dev/null 2>&1 || fail "docker is not installed or not available on PATH."
command -v curl >/dev/null 2>&1 || fail "curl is not installed or not available on PATH."

install -m 0644 "${SERVICE_SRC}" "${SERVICE_DEST}"
install -m 0644 "${WATCHDOG_SERVICE_SRC}" "${WATCHDOG_SERVICE_DEST}"
install -m 0644 "${WATCHDOG_TIMER_SRC}" "${WATCHDOG_TIMER_DEST}"
systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}"
systemctl enable --now "${WATCHDOG_TIMER_NAME}"

printf 'Installed and started %s.\n' "${SERVICE_NAME}"
printf 'Check status with: sudo systemctl status %s\n' "${SERVICE_NAME}"
printf 'Installed and started %s.\n' "${WATCHDOG_TIMER_NAME}"
printf 'Check watchdog logs with: sudo journalctl -u %s -n 100 --no-pager\n' "${WATCHDOG_SERVICE_NAME}"
