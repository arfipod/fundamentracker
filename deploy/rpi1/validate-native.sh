#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="fundamentracker-native.service"
ENV_FILE="/etc/fundamentracker/fundamentracker.env"
BASE_URL="http://127.0.0.1:8000"
RUN_SCAN=0

if [[ "${1:-}" == "--scan" ]]; then
  RUN_SCAN=1
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--scan]" >&2
  exit 2
fi

section() {
  printf '\n==== %s ====\n' "$1"
}

read_env_value() {
  local key="$1"
  python3 - "${ENV_FILE}" "${key}" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
key = sys.argv[2]
for raw in path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    name, value = line.split("=", 1)
    if name.strip() == key:
        print(value.strip())
        break
PY
}

section "Host"
date -Is 2>/dev/null || date
uname -a
free -h
printf 'temperature: '
cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{printf "%.1f C\n", $1/1000}' || true

section "Service"
systemctl is-enabled "${SERVICE_NAME}" || true
systemctl is-active "${SERVICE_NAME}"
systemctl --no-pager --full status "${SERVICE_NAME}" | sed -n '1,25p'

pid="$(systemctl show -p MainPID --value "${SERVICE_NAME}")"
if [[ -n "${pid}" && "${pid}" != "0" && -r "/proc/${pid}/status" ]]; then
  grep -E '^(Name|Pid|VmRSS|VmSize|Threads):' "/proc/${pid}/status" || true
  ps -p "${pid}" -o pid,etimes,%cpu,%mem,rss,vsz,cmd --no-headers || true
fi

section "SQLite"
sqlite_path="$(read_env_value SQLITE_PATH)"
if [[ -z "${sqlite_path}" ]]; then
  echo "SQLITE_PATH is not configured" >&2
  exit 1
fi
ls -lh "${sqlite_path}" 2>/dev/null || true
python3 - "${sqlite_path}" <<'PY'
import sqlite3
import sys
path = sys.argv[1]
with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
    print("integrity_check:", conn.execute("PRAGMA integrity_check").fetchone()[0])
    print("foreign_key_check:", len(conn.execute("PRAGMA foreign_key_check").fetchall()), "violations")
    for table in (
        "tickers", "tags", "ticker_tags", "alerts", "alert_history", "signals",
        "scan_settings", "data_providers", "metric_snapshots", "provider_health",
    ):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count}")
PY

section "API"
api_token="$(read_env_value API_AUTH_TOKEN)"
curl -fsS "${BASE_URL}/health/live"
printf '\n'
curl -fsS -H "Authorization: Bearer ${api_token}" "${BASE_URL}/health/ready"
printf '\n'
curl -fsS -H "Authorization: Bearer ${api_token}" "${BASE_URL}/watchlist" >/tmp/fundamentracker-watchlist-validation.json
python3 - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path("/tmp/fundamentracker-watchlist-validation.json").read_text())
print("watchlist_tickers:", len(payload))
PY
rm -f /tmp/fundamentracker-watchlist-validation.json

if [[ "${RUN_SCAN}" -eq 1 ]]; then
  section "Explicit mutating scan benchmark"
  echo "WARNING: /scan updates alert state/history/signals. This was explicitly requested with --scan."
  start="$(date +%s)"
  curl -fsS -X POST -H "Authorization: Bearer ${api_token}" "${BASE_URL}/scan"
  printf '\n'
  end="$(date +%s)"
  echo "scan_wall_seconds=$((end - start))"
  free -h
  if [[ -n "${pid}" && "${pid}" != "0" && -r "/proc/${pid}/status" ]]; then
    grep -E '^(VmRSS|VmSize|Threads):' "/proc/${pid}/status" || true
  fi
fi

section "Recent service errors"
journalctl -u "${SERVICE_NAME}" -b -p warning --no-pager -n 50 || true

section "Result"
echo "Native validation completed."
if [[ "${RUN_SCAN}" -eq 0 ]]; then
  echo "No scan was executed. Re-run with --scan only on a disposable/final-migration copy when a mutating benchmark is desired."
fi
