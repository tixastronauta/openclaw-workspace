#!/usr/bin/env python3
"""Post Discord progress for the DGES course-detail backfill."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

TARGET = "channel:1485664101756833902"
PID_PATH = Path("projects/dges/data/backfill_course_details_fast.pid")
PROGRESS_PATH = Path("projects/dges/data/backfill_course_details_progress.json")


def send(message: str) -> None:
    subprocess.run(
        ["openclaw", "message", "send", "--channel", "discord", "--target", TARGET, "--message", message],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def read_progress() -> dict:
    if not PROGRESS_PATH.exists():
        return {}
    return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))


def format_progress(prefix: str, progress: dict) -> str:
    return (
        f"{prefix}: {progress.get('percent', '?')}% "
        f"processed={progress.get('processed', '?')}/{progress.get('total', '?')} "
        f"written={progress.get('written', '?')} errors={progress.get('errors', '?')}"
    )


def main() -> int:
    pid = int(PID_PATH.read_text(encoding="utf-8").strip())
    last_bucket = None
    send("DGES detalhes_do_curso: runner rápido ativo. Vou reportar por batches (~40 linhas) e no fim.")

    while process_exists(pid):
        progress = read_progress()
        processed = int(progress.get("processed") or 0)
        bucket = processed // 40
        if progress and bucket != last_bucket:
            send(format_progress("DGES detalhes_do_curso", progress))
            last_bucket = bucket
        time.sleep(45)

    time.sleep(2)
    progress = read_progress()
    if progress:
        status = progress.get("status")
        prefix = "DGES detalhes_do_curso concluído" if status == "completed" else "[blocked] DGES detalhes_do_curso parou"
        msg = format_progress(prefix, progress)
        if "area_cnaef_count" in progress:
            msg += f" area_cnaef_count={progress.get('area_cnaef_count')}"
        send(msg)
    else:
        send("[blocked] DGES detalhes_do_curso parou; progress file missing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
