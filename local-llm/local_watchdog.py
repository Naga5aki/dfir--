"""Windowless scheduled health check; never terminates a busy/loading server."""
from datetime import datetime
from pathlib import Path
from ensure_local_ready import ensure_ready
import subprocess

try:
    ensure_ready()
except (OSError, TimeoutError, subprocess.SubprocessError) as error:
    with Path(r"D:\llm\logs\llama-watchdog.log").open("a", encoding="utf-8") as log:
        log.write(f"{datetime.now().isoformat(timespec='seconds')} readiness_failed {type(error).__name__}; no forced termination\n")
    raise SystemExit(1)
