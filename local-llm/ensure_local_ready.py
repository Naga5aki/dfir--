"""Wait through local-model startup before Hermes sends its first API request."""
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

URL = "http://127.0.0.1:8095/health"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def healthy(url):
    try:
        with OPENER.open(url, timeout=3) as response:
            return json.load(response).get("status") == "ok"
    except (OSError, ValueError, urllib.error.URLError):
        return False


def start_task():
    # IgnoreNew is retained on this task: a model already loading is never killed.
    subprocess.run([
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command",
        "Start-ScheduledTask -TaskName 'llama-server-8095' -ErrorAction Stop",
    ], check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)


def ensure_ready(url=URL, timeout=150, interval=1, start=start_task):
    if healthy(url):
        return
    start()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if healthy(url):
            return
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
    raise TimeoutError("Local model was not ready after 150 seconds; see D:/llm/logs/server-console.log")


def main():
    # Hermes hook payload may contain private text. Consume without storing or logging it.
    if "--hook" in sys.argv:
        sys.stdin.read()
    try:
        ensure_ready()
    except (OSError, subprocess.SubprocessError, TimeoutError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print("{}" if "--hook" in sys.argv else '{"status":"ok"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
