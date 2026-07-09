#!/usr/bin/env bash
set -u

echo "[CAMERA] Initializing Nikon D5600 for photobooth..."

# Do not use set -e here.
# Some Nikon/gphoto2 settings are mode-dependent and may fail temporarily.
# A failed optional setting should not stop the photobooth from starting.

SLEEP_AFTER_SET=0.30

set_cam() {
    local key="$1"
    local value="$2"

    echo "[CAMERA] set ${key}=${value}"
    if gphoto2 --set-config "${key}=${value}"; then
        sleep "$SLEEP_AFTER_SET"
        return 0
    else
        echo "[CAMERA] WARNING: could not set ${key}=${value}" >&2
        return 1
    fi
}

set_cam_index() {
    local key="$1"
    local index="$2"

    echo "[CAMERA] set-index ${key}=${index}"
    if gphoto2 --set-config-index "${key}=${index}"; then
        sleep "$SLEEP_AFTER_SET"
        return 0
    else
        echo "[CAMERA] WARNING: could not set-index ${key}=${index}" >&2
        return 1
    fi
}

echo "[CAMERA] Checking camera..."

if ! gphoto2 --summary >/dev/null 2>&1; then
    echo "[CAMERA] ERROR: camera not reachable via gphoto2" >&2
    exit 1
fi

echo "[CAMERA] Basic image settings..."

# Image size:
# Choice 0 = 6000x4000
# Choice 1 = 4496x3000
# Choice 2 = 2992x2000
set_cam_index /main/imgsettings/imagesize 1 || true

# Give the camera a moment after changing image size.
sleep 1.0

# JPEG Fine.
# This may fail transiently on the D5600; not fatal.
# Your final state already showed JPEG Fine, so this is only a best-effort setting.
# set_cam_index /main/imgsettings/imagequality 2 || true

echo "[CAMERA] Exposure settings..."

# The physical mode dial should be on A.
# In A mode, f-number is writable.
# For your current zoom position, index 3 = f/5.6.
set_cam_index /main/capturesettings/f-number 3 || true

# Exposure metering:
# Your available options:
#   index 0 = Center Weighted
#   index 1 = Multi Spot
#   index 2 = Center Spot
#
# Center Spot was too unstable for photobooth use.
set_cam_index /main/capturesettings/exposuremetermode 0 || true

# Exposure compensation:
# index 14 = -0.3 EV
# index 15 =  0.0 EV
#
# Use -0.3 EV to protect highlights without making everything too dark.
# IMPORTANT: use index here, not value -333.
set_cam_index /main/capturesettings/exposurecompensation 14 || true

echo "[CAMERA] ISO settings..."

# Auto ISO is inconsistent on this camera via gphoto2:
# one property may be writable, another may throw "PTP Access Denied".
# For reliability, use fixed ISO 800.
#
# ISO choices from your camera:
# index 6  = ISO 400
# index 9  = ISO 800
# index 12 = ISO 1600
#
# ISO 800 is a good starting point for indoor photobooth use:
# much safer shutter times than ISO 100, still acceptable noise.
set_cam_index /main/imgsettings/iso 12 || true

echo "[CAMERA] White balance..."

# White balance:
# Use Auto white balance.
# On this Nikon/gphoto2 setup, use index, not raw value.
# Your previous "whitebalance=2" kept/set Fluorescent.
set_cam_index /main/imgsettings/whitebalance 0 || true

echo "[CAMERA] Autofocus settings..."

# Still AF mode: AF-S.
set_cam_index /main/capturesettings/focusmode2 0 || true

# Live View AF mode:
# index 0 = Face-priority AF.
set_cam_index /main/capturesettings/liveviewafmode 0 || true

# Live View AF focus:
# index 1 = Full-time-servo AF.
# This should let the camera focus while people position themselves,
# so the capture after the countdown can happen with minimal delay.
set_cam_index /main/capturesettings/liveviewaffocus 1 || true

# Do NOT set /main/capturesettings/autofocusarea here.
# The D5600 rejected autofocusarea=0 in Face-priority mode.

# Do NOT set /main/capturesettings/focusmetermode here for now.
# Your camera returned PTP Access Denied and stayed on Single Area.
# Live-view Face-priority AF is the more relevant setting for the preview flow.

echo "[CAMERA] Final relevant camera state:"
gphoto2 --summary | grep -Ei \
"Image Size|Compression Setting|White Balance|F-Number|Focal Length|Focus Mode|Exposure Metering Mode|Exposure Time|Exposure Program Mode|Exposure Index|Exposure Bias|Auto ISO|ISO Auto|Focus Metering Mode|Live View AF|Autofocus Mode|AF Locked|Active AF Sensor" \
|| true

echo "[CAMERA] init_camera.sh done."
