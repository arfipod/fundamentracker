#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="fundamentracker.service"
SYSTEMD_DIR="/etc/systemd/system"
PROJECT_DIR="/opt/fundamentracker"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_SRC="${REPO_ROOT}/systemd/${SERVICE_NAME}"
SERVICE_DEST="${SYSTEMD_DIR}/${SERVICE_NAME}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

if [[ "${EUID}" -ne 0 ]]; then
  fail "this installer must be run with sudo or as root."
fi

[[ -f "${SERVICE_SRC}" ]] || fail "missing service file: ${SERVICE_SRC}"
[[ -d "${PROJECT_DIR}" ]] || fail "project directory does not exist: ${PROJECT_DIR}"
[[ -f "${PROJECT_DIR}/docker-compose.prod.yml" ]] || fail "missing production compose file: ${PROJECT_DIR}/docker-compose.prod.yml"
command -v docker >/dev/null 2>&1 || fail "docker is not installed or not available on PATH."

install -m 0644 "${SERVICE_SRC}" "${SERVICE_DEST}"
systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}"

printf 'Installed and started %s.\n' "${SERVICE_NAME}"
printf 'Check status with: sudo systemctl status %s\n' "${SERVICE_NAME}"
