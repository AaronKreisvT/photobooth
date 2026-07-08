# Photobooth

A Raspberry-Pi-based DSLR photo booth with a fullscreen touchscreen interface, template-based image composition and direct printing.

The project is built for real event use: guests select a layout, the camera takes one, two or four photos, the software combines them with a configurable template, and the final image can be printed directly on a photo printer.

## Status

Work in progress, but already usable at private events.

The current version focuses on a robust local setup. Earlier prototypes included server-side synchronization and QR-code sharing, but this repository currently contains the local photobooth software only.

## Features

- Fullscreen PyQt6 kiosk interface
- DSLR live preview and image capture via `gphoto2`
- Capture workflows for 1, 2 or 4 photos
- Template-based image composition
- Configurable template text, for example names and dates
- Local storage of final images
- Direct printing via CUPS
- Local print statistics
- Idle / screensaver mode
- Keyboard shortcuts for setup and operation

## Hardware

The system is designed around:

- Raspberry Pi
- DSLR camera connected via USB
- Touchscreen
- DNP photo printer or another CUPS-compatible photo printer
- Custom enclosure

The exact hardware can be adapted, but the current setup was developed and tested with a Raspberry Pi, a USB-controlled DSLR camera and a DNP photo printer.

## Software stack

- Python
- PyQt6
- gphoto2
- CUPS
- Pillow
- Bash scripts for startup and camera initialization

## Project structure

```text
photobooth/
├── assets/              # UI assets, fonts, example templates
├── fotobox/             # Main Python application package
├── photos/              # Local output images, ignored by Git
├── photos-tmp/          # Temporary captures, ignored by Git
├── tools/               # Helper scripts
├── main.py              # Application entry point
├── run.sh               # Startup script
├── settings.example.json
└── README.md
