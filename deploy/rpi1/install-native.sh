#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="fundamentracker-native.service"
PROJECT_DIR="/opt/fundamentracker"
DATA_DIR="/srv/fundamentracker"
CONFIG_DIR="/etc/fundamentracker"
CONFIG_FILE="${CONFIG_DIR}/fundamentracker.env"
SYSTEMD_DIR="/etc/systemd/system"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SERVICE_SRC="${SCRIPT_DIR}/fundamentracker-native.service"
ENV_EXAMPLE="${SCRIPT_DIR}/fundamentracker.env.example"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

if [[ "${EUID}" -ne 0 ]]; then
  fail "run this installer with sudo or as root"
fi

if [[ "$(realpath "${REPO_ROOT}")" != "${PROJECT_DIR}" ]]; then
  fail "native deployment expects the Git checkout at ${PROJECT_DIR}; clone/update the repository there first"
fi

[[ -d "${PROJECT_DIR}/.git" ]] || fail "${PROJECT_DIR} is not a Git checkout"
[[ -f "${SERVICE_SRC}" ]] || fail "missing service file: ${SERVICE_SRC}"
[[ -f "${ENV_EXAMPLE}" ]] || fail "missing environment template: ${ENV_EXAMPLE}"
command -v python3 >/dev/null 2>&1 || fail "python3 is not installed"

if ! getent group fundamentracker >/dev/null; then
  groupadd --system fundamentracker
fi
if ! getent passwd fundamentracker >/dev/null; then
  useradd --system \
    --gid fundamentracker \
    --home-dir /nonexistent \
    --no-create-home \
    --shell /usr/sbin/nologin \
    --comment "FundamenTracker API" \
    fundamentracker
fi

install -d -o root -g fundamentracker -m 0750 "${CONFIG_DIR}"
install -d -o fundamentracker -g fundamentracker -m 0750 "${DATA_DIR}"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  install -o root -g fundamentracker -m 0640 "${ENV_EXAMPLE}" "${CONFIG_FILE}"
  printf 'Created %s from the example. Edit its secrets before enabling the service.\n' "${CONFIG_FILE}"
fi

if [[ ! -x "${PROJECT_DIR}/.venv/bin/python" ]]; then
  cat >&2 <<EOF
ERROR: ${PROJECT_DIR}/.venv is not prepared.
Run deploy/rpi1/probe-runtime.sh first, then create and validate the virtualenv
using the package strategy selected from that probe. The service has NOT been
installed.
EOF
  exit 2
fi

if ! PYTHONPATH="${PROJECT_DIR}/api" \
  "${PROJECT_DIR}/.venv/bin/python" -c \
  'import fastapi, uvicorn, pandas, yfinance; import api.api' >/dev/null; then
  fail "native runtime import check failed; service was not installed"
fi

if grep -q '^API_AUTH_TOKEN=change-me-api-token$' "${CONFIG_FILE}"; then
  fail "replace the placeholder API_AUTH_TOKEN in ${CONFIG_FILE} before installing the service"
fi

install -o root -g root -m 0644 \
  "${SERVICE_SRC}" "${SYSTEMD_DIR}/${SERVICE_NAME}"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

printf 'Installed and started %s.\n' "${SERVICE_NAME}"
printf 'Status: sudo systemctl status %s\n' "${SERVICE_NAME}"
printf 'Logs:   sudo journalctl -u %s -b --no-pager\n' "${SERVICE_NAME}"
