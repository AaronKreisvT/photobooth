#!/usr/bin/env bash
set -u

PRINTER="${1:-DS620}"

echo "[PRINTER] Checking whether DS620 is visible via USB..."

if lpinfo -v 2>/dev/null | grep -Eiq "dnp|ds620|DB6C57099135"; then
    echo "[PRINTER] DS620 appears to be visible via USB."
else
    echo "[PRINTER] WARNING: DS620 not detected via USB."
    echo "[PRINTER] Check: printer power cable to wall, USB cable from printer to Raspberry Pi."
fi

echo "[PRINTER] Reset printer queue for: $PRINTER"

echo "[PRINTER] Status before reset:"
lpstat -t || true
lpstat -o "$PRINTER" || true

echo "[PRINTER] Cancel pending jobs for $PRINTER..."
cancel -a "$PRINTER" || true

echo "[PRINTER] Enable printer queue..."
cupsenable "$PRINTER" || true

echo "[PRINTER] Accept new jobs..."
cupsaccept "$PRINTER" || true

echo "[PRINTER] Status after reset:"
lpstat -t || true
lpstat -o "$PRINTER" || true

echo "[PRINTER] Reset done."
