# fotobox/settings_store.py
from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from typing import List, Tuple

REQUIRED_TEMPLATE_FILES = ("template.json", "single_bg.png", "double_bg.png", "quadruple_bg.png")

@dataclass
class Settings:
    IDLE_SECONDS_TO_SCREENSAVER: int = 180
    FINAL_IDLE_TIMEOUT_SECONDS: int = 45
    PREVIEW_COUNTDOWN_SECONDS: int = 5
    DEFAULT_TEXT_LINE1: str = ""
    DEFAULT_TEXT_LINE2: str = ""
    TEMPLATE_NAME: str = "default"  # subfolder name under assets/templates/

def settings_path(root_dir: str) -> str:
    return os.path.join(root_dir, "settings.json")

def load_settings(root_dir: str, defaults: Settings) -> Settings:
    p = settings_path(root_dir)
    if not os.path.exists(p):
        return defaults
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        s = Settings(**{**asdict(defaults), **data})
        return s
    except Exception:
        return defaults

def save_settings(root_dir: str, s: Settings) -> None:
    p = settings_path(root_dir)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(asdict(s), f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)

def scan_templates(root_dir: str) -> List[str]:
    """Return list of valid template subfolder names."""
    base = os.path.join(root_dir, "assets", "templates")
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if not os.path.isdir(d):
            continue
        ok = all(os.path.exists(os.path.join(d, fn)) for fn in REQUIRED_TEMPLATE_FILES)
        if ok:
            out.append(name)
    return out

def template_paths(root_dir: str, template_name: str) -> Tuple[str, str, str]:
    """Returns (single_bg, double_bg, quadruple_bg) absolute paths."""
    d = os.path.join(root_dir, "assets", "templates", template_name)
    return (
        os.path.join(d, "single_bg.png"),
        os.path.join(d, "double_bg.png"),
        os.path.join(d, "quadruple_bg.png"),
    )

