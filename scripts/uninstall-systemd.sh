#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="fundamentracker.service"
WATCHDOG_SERVICE_NAME="fundamentracker-watchdog.service"
WATCHDOG_TIMER_NAME="fundamentracker-watchdog.timer"
SERVICE_DEST="/etc/systemd/system/${SERVICE_NAME}"
WATCHDOG_SERVICE_DEST="/etc/systemd/system/${WATCHDOG_SERVICE_NAME}"
WATCHDOG_TIMER_DEST="/etc/systemd/system/${WATCHDOG_TIMER_NAME}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

if [[ "${EUID}" -ne 0 ]]; then
  fail "this uninstaller must be run with sudo or as root."
fi

if systemctl list-unit-files --type=timer --no-legend | awk '{print $1}' | grep -Fxq "${WATCHDOG_TIMER_NAME}"; then
  systemctl disable --now "${WATCHDOG_TIMER_NAME}"
elif systemctl list-units --type=timer --all --no-legend | awk '{print $1}' | grep -Fxq "${WATCHDOG_TIMER_NAME}"; then
  systemctl stop "${WATCHDOG_TIMER_NAME}"
fi

if systemctl list-units --type=service --all --no-legend | awk '{print $1}' | grep -Fxq "${WATCHDOG_SERVICE_NAME}"; then
  systemctl stop "${WATCHDOG_SERVICE_NAME}" || true
fi

if systemctl list-unit-files --type=service --no-legend | awk '{print $1}' | grep -Fxq "${SERVICE_NAME}"; then
  systemctl disable --now "${SERVICE_NAME}"
elif systemctl list-units --type=service --all --no-legend | awk '{print $1}' | grep -Fxq "${SERVICE_NAME}"; then
  systemctl stop "${SERVICE_NAME}"
fi

rm -f "${SERVICE_DEST}"
rm -f "${WATCHDOG_SERVICE_DEST}" "${WATCHDOG_TIMER_DEST}"
systemctl daemon-reload
systemctl reset-failed "${SERVICE_NAME}" >/dev/null 2>&1 || true
systemctl reset-failed "${WATCHDOG_SERVICE_NAME}" >/dev/null 2>&1 || true
systemctl reset-failed "${WATCHDOG_TIMER_NAME}" >/dev/null 2>&1 || true

printf 'Uninstalled %s, %s, and %s.\n' "${SERVICE_NAME}" "${WATCHDOG_SERVICE_NAME}" "${WATCHDOG_TIMER_NAME}"
