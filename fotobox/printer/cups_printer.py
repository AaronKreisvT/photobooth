from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, Tuple

# Counter file (stored in root_dir/printer_stats.json)
STATS_FILENAME = "printer_stats.json"


@dataclass(frozen=True)
class PrintResult:
    ok: bool
    error: Optional[str] = None
    job_id: Optional[str] = None


def _run_lp(args: list[str]) -> Tuple[int, str]:
    """Run lp and return (exit_code, combined_output)."""
    p = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return p.returncode, p.stdout.strip()


def printer_available() -> bool:
    """Check if the configured printer exists in CUPS."""
    code, out = _run_lp(["lpstat", "-p", "DS620"])
    return code == 0


def submit_print_job(image_path: str, copies: int = 1) -> PrintResult:
    """
    Submit a print job to CUPS using lp. This only queues the job.
    Returns PrintResult with optional job_id.
    """
    if copies <= 0:
        return PrintResult(ok=True)

    if not os.path.exists(image_path):
        return PrintResult(ok=False, error=f"File not found: {image_path}")

    # Quick availability check (fast fail)
    if not printer_available():
        return PrintResult(ok=False, error=f"Printer '{DS620}' not available")

    # DS620 expects 4x6 @ 300dpi; your image already matches.
    args = [
        "lp",
        "-d", "DS620",
        "-n", str(copies),
        "-o", "PageSize=w288h432",
        "-o", "Resolution=300dpi",
        "-o", "StpiShrinkOutput=Shrink",
        image_path,
    ]

    code, out = _run_lp(args)
    if code != 0:
        return PrintResult(ok=False, error=out or "lp failed")

    # lp often prints something like: "request id is DS620-123 (1 file(s))"
    job_id = None
    if "request id is" in out:
        try:
            job_id = out.split("request id is", 1)[1].strip().split()[0]
        except Exception:
            job_id = None

    return PrintResult(ok=True, job_id=job_id)


def _load_stats(path: str) -> dict:
    if not os.path.exists(path):
        return {"total_jobs": 0, "total_copies": 0, "last_job_ts": None, "history": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"total_jobs": 0, "total_copies": 0, "last_job_ts": None, "history": []}


def _save_stats(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def record_print(root_dir: str, copies: int, job_id: Optional[str], image_path: str) -> None:
    """Persistently record submitted prints for later inspection."""
    stats_path = os.path.join(root_dir, STATS_FILENAME)
    data = _load_stats(stats_path)

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    data["total_jobs"] = int(data.get("total_jobs", 0)) + 1
    data["total_copies"] = int(data.get("total_copies", 0)) + int(copies)
    data["last_job_ts"] = ts

    hist = data.get("history", [])
    hist.append({
        "ts": ts,
        "copies": int(copies),
        "job_id": job_id,
        "file": os.path.basename(image_path),
    })

    # keep history bounded (avoid endless growth)
    if len(hist) > 200:
        hist = hist[-200:]
    data["history"] = hist

    _save_stats(stats_path, data)
