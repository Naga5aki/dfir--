"""Bounded DFIR dependency checks; never starts, installs or analyzes anything."""
from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import shutil
import socket
from urllib.parse import urlsplit

PROFILES = Path(__file__).resolve().parent.parent / "profiles"
NAMES = ("dfir", "dfir-myos", "dfir-re", "dfir-mem", "dfir-pcap", "dfir-max")


def transport_check(name, host, port, *, probe, timeout):
    row = {"server": name, "kind": "tcp_transport", "host": host, "port": port,
           "business_health_verified": False}
    try:
        loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = False
    if not probe or not loopback:
        return {**row, "status": "not_probed", "detail": "Only explicit loopback probes are allowed"}
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {**row, "status": "reachable", "detail": "TCP only; no MCP or business operation called"}
    except OSError:
        return {**row, "status": "failed", "detail": "Loopback endpoint unreachable; no automatic restart"}


def inspect_server(name, config, *, probe=False, timeout=1.0):
    checks = []
    if config.get("enabled", True) is False:
        return [{"server": name, "kind": "configuration", "status": "disabled"}]
    if config.get("url"):
        url = urlsplit(config["url"])
        checks.append(transport_check(name, url.hostname or "", url.port or (443 if url.scheme == "https" else 80),
                                      probe=probe, timeout=timeout))
    else:
        command = str(config.get("command") or "")
        exists = Path(command).is_file() if ("/" in command or "\\" in command) else bool(shutil.which(command))
        checks.append({"server": name, "kind": "executable", "status": "present" if exists else "failed",
                       "path": command, "business_health_verified": False})
    if config.get("cwd"):
        cwd = Path(config["cwd"])
        checks.append({"server": name, "kind": "cwd", "status": "present" if cwd.is_dir() else "failed",
                       "path": str(cwd)})
    if name == "jadx":
        checks.append(transport_check("jadx-plugin", "127.0.0.1", 8650, probe=probe, timeout=timeout))
    if name == "wiremcp":
        candidate = Path(r"D:\ForensicsAgent\tools\wireshark\tshark.exe")
        checks.append({"server": name, "kind": "tshark", "path": str(candidate),
                       "status": "present" if candidate.is_file() else "failed"})
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, choices=NAMES)
    parser.add_argument("--profiles-root", type=Path, default=PROFILES)
    parser.add_argument("--probe", action="store_true", help="Probe only configured loopback TCP endpoints")
    parser.add_argument("--timeout", type=float, default=1.0)
    args = parser.parse_args()
    if not 0 < args.timeout <= 5:
        parser.error("timeout must be between 0 and 5 seconds")
    from ruamel.yaml import YAML
    yaml = YAML(typ="safe")
    yaml.allow_duplicate_keys = False
    home = args.profiles_root.resolve() / args.profile
    try:
        config = yaml.load((home / "config.yaml").read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(json.dumps({"profile": args.profile, "error": type(exc).__name__,
                          "detail": "Configuration could not be parsed; no files changed"}))
        return 2
    checks = []
    model = config.get("providers", {}).get(config.get("model", {}).get("provider"), {})
    if model.get("base_url"):
        checks.extend(inspect_server("model", {"url": model["base_url"]}, probe=args.probe, timeout=args.timeout))
    for name, server in config.get("mcp_servers", {}).items():
        checks.extend(inspect_server(name, server, probe=args.probe, timeout=args.timeout))
    terminal = config.get("terminal", {})
    if terminal.get("backend") == "ssh":
        checks.append(transport_check("kali-ssh", terminal.get("ssh_host", ""), int(terminal.get("ssh_port", 22)),
                                      probe=args.probe, timeout=args.timeout))
        checks.append({"server": "kali-ssh", "kind": "remote_cwd", "path": terminal.get("cwd"),
                       "status": "unverified" if str(terminal.get("cwd", "")).startswith("/") else "needs_review",
                       "detail": "Requires authenticated identity/mount verification; this script never logs in"})
    failed = sum(check.get("status") == "failed" for check in checks)
    print(json.dumps({"profile": args.profile, "failed_checks": failed, "end_to_end_health_verified": False,
                      "checks": checks, "next_step": "Resolve failed dependencies; never infer business health from registration"},
                     ensure_ascii=False, indent=2))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
