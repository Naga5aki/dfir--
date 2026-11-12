"""Scheduled-task entry point: own a console-free child for its entire lifetime."""
import json
import os
from pathlib import Path
import subprocess
import sys


def run_server(command, cwd, log_path):
    env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    with open(log_path, "ab", buffering=0) as log:
        process = subprocess.Popen(command, cwd=cwd, env=env,
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)
        return process.wait()


def main():
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("server-config.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return run_server(config["command"], config["cwd"], config["log_path"])


if __name__ == "__main__":
    raise SystemExit(main())
