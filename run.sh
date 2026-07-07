#!/usr/bin/env bash
set -e

export DISPLAY=:0
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

xset s off || true
xset s noblank || true
xset -dpms || true
xset s 0 0 || true

xset -cursor_name none || true

bash "$SCRIPT_DIR/init_camera.sh"

#PYTHONUNBUFFERED=1 "$SCRIPT_DIR/venv/bin/python" -u \
#  "$SCRIPT_DIR/tools/calibrate_overlay.py" \
#  "$SCRIPT_DIR/assets/splash.png" \
#  --log "$SCRIPT_DIR/calibrate.log"

"$SCRIPT_DIR/venv/bin/python" -u "$SCRIPT_DIR/main.py"
