from __future__ import annotations
import json
import os

def _template_dir(root_dir: str, template_name: str) -> str:
    return os.path.join(root_dir, "assets", "templates", template_name)

def load_template_variant(root_dir: str, template_name: str, n: int) -> dict:
    tdir = _template_dir(root_dir, template_name)
    path = os.path.join(tdir, "template.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    variants = data.get("variants", {})
    variant = variants.get(str(n))
    if variant is None:
        raise KeyError(f"Template '{template_name}' has no variant '{n}' in template.json")

    # Basic validation
    slots = variant.get("slots_px")
    if not isinstance(slots, list) or len(slots) != n:
        raise ValueError(f"Template '{template_name}' variant {n}: slots_px must have length {n}")

    text_fields = variant.get("text_fields_px", {})
    if not isinstance(text_fields, dict):
        raise ValueError(f"Template '{template_name}' variant {n}: text_fields_px must be a dict")

    return variant

def background_path(root_dir: str, template_name: str, n: int) -> str:
    tdir = _template_dir(root_dir, template_name)
    filename = {1: "single_bg.png", 2: "double_bg.png", 4: "quadruple_bg.png"}[n]
    return os.path.join(tdir, filename)
