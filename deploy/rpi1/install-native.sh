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

[[ -f "${SERVICE_SRC}" ]] || fail "missing service file: ${SERVICE_SRC}"
[[ -f "${ENV_EXAMPLE}" ]] || fail "missing environment template: ${ENV_EXAMPLE}"
command -v python3 >/dev/null 2>&1 || fail "python3 is not installed"
command -v tar >/dev/null 2>&1 || fail "tar is not installed"

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
install -d -o root -g fundamentracker -m 0755 "${PROJECT_DIR}"

# Stage code without touching the persistent SQLite/data directory. When the
# checkout itself already lives in /opt/fundamentracker, no copy is necessary.
if [[ "$(realpath "${REPO_ROOT}")" != "$(realpath "${PROJECT_DIR}")" ]]; then
  tar \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='frontend/node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -C "${REPO_ROOT}" -cf - . | tar -C "${PROJECT_DIR}" -xf -
fi
chown -R root:fundamentracker "${PROJECT_DIR}"
find "${PROJECT_DIR}" -type d -exec chmod a-w {} +
find "${PROJECT_DIR}" -type f -exec chmod a-w {} +

if [[ ! -f "${CONFIG_FILE}" ]]; then
  install -o root -g fundamentracker -m 0640 "${ENV_EXAMPLE}" "${CONFIG_FILE}"
  printf 'Created %s from the example. Edit its secrets before enabling the service.\n' "${CONFIG_FILE}"
fi

if [[ ! -x "${PROJECT_DIR}/.venv/bin/python" ]]; then
  cat >&2 <<EOF
ERROR: ${PROJECT_DIR}/.venv is not prepared.
Run the ARMv6 runtime probe first, then create/validate the virtualenv using the
package strategy selected from that probe. The service has NOT been installed.
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
