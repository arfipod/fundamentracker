#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="fundamentracker.service"
SERVICE_DEST="/etc/systemd/system/${SERVICE_NAME}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

if [[ "${EUID}" -ne 0 ]]; then
  fail "this uninstaller must be run with sudo or as root."
fi

if systemctl list-unit-files --type=service --no-legend | awk '{print $1}' | grep -Fxq "${SERVICE_NAME}"; then
  systemctl disable --now "${SERVICE_NAME}"
elif systemctl list-units --type=service --all --no-legend | awk '{print $1}' | grep -Fxq "${SERVICE_NAME}"; then
  systemctl stop "${SERVICE_NAME}"
fi

rm -f "${SERVICE_DEST}"
systemctl daemon-reload
systemctl reset-failed "${SERVICE_NAME}" >/dev/null 2>&1 || true

printf 'Uninstalled %s.\n' "${SERVICE_NAME}"
