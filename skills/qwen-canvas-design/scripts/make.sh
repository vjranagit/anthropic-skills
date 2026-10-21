#!/usr/bin/env bash
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="$SKILL_DIR/.venv/bin/python"
test -x "$PY" || { echo '{"ok":false,"error":"run scripts/setup.sh first"}'; exit 1; }
"$PY" "$(dirname "$0")/build.py" "${1:?usage: make.sh content.json out-dir}" "${2:?usage: make.sh content.json out-dir}"
