#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TMP_ROOT="$(mktemp -d -t fundamentracker-rpi1-probe.XXXXXX)"
trap 'rm -rf "${TMP_ROOT}"' EXIT

section() {
  printf '\n==== %s ====\n' "$1"
}

run_optional() {
  printf '+ %q' "$1"
  shift
  printf ' %q' "$@"
  printf '\n'
  "$@" 2>&1 || true
}

section "Host"
date -Is 2>/dev/null || date
uname -a
printf 'machine: '; uname -m
printf 'dpkg architecture: '; dpkg --print-architecture 2>/dev/null || printf 'n/a\n'
printf 'CPU model: '
tr '\0' '\n' </proc/device-tree/model 2>/dev/null || true
printf '\n'
cat /etc/os-release 2>/dev/null || true

section "Capacity"
free -h 2>/dev/null || true
df -h / 2>/dev/null || true
printf 'swap:\n'
swapon --show 2>/dev/null || true

section "Python"
python3 --version || true
python3 - <<'PY'
import platform
import sqlite3
import sys
print("executable:", sys.executable)
print("python:", sys.version.replace("\n", " "))
print("platform:", platform.platform())
print("sqlite:", sqlite3.sqlite_version)
PY

section "Existing relevant distro packages"
for package in \
  python3-venv python3-dev python3-numpy python3-pandas python3-lxml \
  python3-cffi python3-cryptography build-essential libffi-dev libxml2-dev libxslt1-dev; do
  printf '\n-- %s --\n' "${package}"
  apt-cache policy "${package}" 2>/dev/null | sed -n '1,6p' || true
done

section "Existing imports"
python3 - <<'PY'
modules = [
    "fastapi", "uvicorn", "numpy", "pandas", "yfinance", "curl_cffi",
    "lxml", "cffi", "pydantic_core", "google.genai",
]
for module in modules:
    try:
        imported = __import__(module, fromlist=["*"])
        version = getattr(imported, "__version__", "unknown")
        print(f"OK   {module}: {version}")
    except Exception as exc:
        print(f"MISS {module}: {type(exc).__name__}: {exc}")
PY

section "Virtualenv capability"
if ! python3 -m venv "${TMP_ROOT}/venv"; then
  echo "RESULT venv=FAILED"
  echo "Install python3-venv before attempting a native deployment."
  exit 0
fi
"${TMP_ROOT}/venv/bin/python" -m pip --version || true

section "Exact requirements wheel availability"
mkdir -p "${TMP_ROOT}/wheels"
set +e
"${TMP_ROOT}/venv/bin/python" -m pip download \
  --disable-pip-version-check \
  --only-binary=:all: \
  --dest "${TMP_ROOT}/wheels" \
  -r "${REPO_ROOT}/requirements.txt"
wheel_status=$?
set -e
if [[ "${wheel_status}" -eq 0 ]]; then
  echo "RESULT exact_binary_requirements=AVAILABLE"
else
  echo "RESULT exact_binary_requirements=NOT_FULLY_AVAILABLE"
  echo "This is diagnostic only: Raspberry Pi OS packages or adjusted pins may still provide a valid runtime."
fi

section "Key package wheel checks"
for requirement in \
  'numpy==2.4.4' \
  'pandas==3.0.2' \
  'curl_cffi==0.15.0' \
  'cffi==2.0.0' \
  'lxml' \
  'pydantic-core' \
  'yfinance==1.5.2'; do
  printf '%-24s ' "${requirement}"
  rm -rf "${TMP_ROOT}/one"
  mkdir -p "${TMP_ROOT}/one"
  if "${TMP_ROOT}/venv/bin/python" -m pip download \
      --disable-pip-version-check \
      --only-binary=:all: \
      --no-deps \
      --dest "${TMP_ROOT}/one" \
      "${requirement}" >/dev/null 2>&1; then
    echo AVAILABLE
  else
    echo MISSING
  fi
done

section "Cloudflare Tunnel"
if command -v cloudflared >/dev/null 2>&1; then
  cloudflared --version || true
else
  echo "cloudflared: not installed"
fi
apt-cache policy cloudflared 2>/dev/null | sed -n '1,8p' || true

section "Network smoke"
if command -v curl >/dev/null 2>&1; then
  curl -fsS --max-time 10 -o /dev/null -w 'pypi_http=%{http_code}\n' https://pypi.org/ || echo "pypi_http=FAILED"
else
  echo "curl: not installed"
fi

section "Result"
echo "Probe completed without modifying system packages or services."
echo "Temporary downloads and the probe virtualenv were removed automatically."
