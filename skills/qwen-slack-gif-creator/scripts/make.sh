#!/usr/bin/env bash
# usage: make.sh content.json out-dir  -> out-dir/animation.gif + out-dir/frames/step_NN.png
# Prints one JSON line on success; on bad content prints "FIX: ..." and exits 2.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONTENT=${1:?usage: make.sh content.json out-dir}
OUT=${2:?usage: make.sh content.json out-dir}
PYTHON="$SKILL_DIR/.venv/bin/python"
test -x "$PYTHON" || { echo "run scripts/setup.sh first" >&2; exit 1; }
mkdir -p "$OUT"
SLACK_GIF_ROOT="$SKILL_DIR" exec "$PYTHON" "$(dirname "$(readlink -f "$0")")/render.py" "$CONTENT" "$OUT"
