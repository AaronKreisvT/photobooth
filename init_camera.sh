#!/bin/bash
sleep 2
gphoto2 --auto-detect >/dev/null 2>&1 || exit 0

gphoto2 \
  --set-config capturetarget=1 \
  --set-config /main/imgsettings/imagesize=4496x3000 \
  --set-config /main/capturesettings/imagequality=2 \
  --set-config /main/imgsettings/iso=100 \
  --set-config /main/imgsettings/autoiso=0 \
  --set-config /main/imgsettings/whitebalance=2 \
  --set-config /main/capturesettings/exposurecompensation=0 \
  --set-config /main/capturesettings/exposuremetermode=2 \
  --set-config /main/capturesettings/dlighting=0 \
  --set-config /main/capturesettings/highisonr=2
