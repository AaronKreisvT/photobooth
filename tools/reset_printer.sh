#!/usr/bin/env bash
set -u

PRINTER="${1:-DS620}"

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
