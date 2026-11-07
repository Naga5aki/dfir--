#!/usr/bin/env python3
"""Reload the local Hermes backend after a credential value change in .env.

Why: `hermes mcp test <name>` runs in a fresh process and reads the new .env,
but the running desktop backend (`hermes serve`) keeps its cached values, so
its reconnect loop keeps failing (401) and the MCP tool set never joins the
session. The fix is to fire the gateway JSON-RPCs `reload.env` then `reload.mcp`.

Usage:
    pip install websockets
    python reload_mcp_gateway.py              # discover loopback backends, reload
    python reload_mcp_gateway.py --dry-run    # discovery only, send nothing
    python reload_mcp_gateway.py --port P     # target one backend explicitly

Verify by EVIDENCE, not the RPC reply: `reload.mcp` runs asynchronously and may
not answer within any client timeout (normal). Check the backend log
(`.../hermes/logs/agent.log`) for:   MCP server '<name>': registered N tool(s)
then confirm via tool_search -- the session catalog is live.

Localhost only; the token is read from the backend's own loopback page and
must not be printed or forwarded.
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
import urllib.request

try:
    import websockets
except ImportError:  # pragma: no cover
    sys.exit("missing dependency: pip install websockets  (or uv pip install websockets)")

TOKEN_RE = re.compile(r'__HERMES_SESSION_TOKEN__="([^"]+)"')
MARKER = "Headless backend (hermes serve)"


def listener_ports():
    """Loopback LISTENING ports (netstat on Windows; ss/lsof on POSIX)."""
    for cmd in (["netstat", "-ano"], ["ss", "-ltn"], ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
        except Exception:
            continue
        if not out:
            continue
        ports = set()
        for line in out.splitlines():
            if "LISTEN" not in line.upper():
                continue
            m = re.search(r"127\.0\.0\.1[:.](\d+)", line)
            if m:
                ports.add(int(m.group(1)))
        if ports:
            return sorted(ports)
    return []


def probe(port):
    """Return the session token if this port serves a hermes headless backend."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=1.5) as resp:
            body = resp.read(4096).decode("utf-8", "replace")
    except Exception:
        return None
    if MARKER not in body:
        return None
    m = TOKEN_RE.search(body)
    return m.group(1) if m else None


async def _wait_reply(ws, rid, timeout):
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if data.get("id") == rid:
            return data


async def reload_one(port, token, dry):
    print("[+] backend on 127.0.0.1:%d" % port)
    if dry:
        return
    url = "ws://127.0.0.1:%d/api/ws?token=%s" % (port, token)
    async with websockets.connect(url, open_timeout=8) as ws:
        await ws.send(json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "reload.env", "params": {}}))
        try:
            data = await _wait_reply(ws, 1, 20)
            print("    reload.env -> %s" % json.dumps(data.get("result")))
        except asyncio.TimeoutError:
            print("    reload.env -> no reply within 20s")
        await ws.send(json.dumps(
            {"jsonrpc": "2.0", "id": 2, "method": "reload.mcp", "params": {"confirm": True}}))
        try:
            data = await _wait_reply(ws, 2, 30)
            print("    reload.mcp -> %s" % json.dumps(data.get("result")))
        except asyncio.TimeoutError:
            print("    reload.mcp -> no reply within 30s (async is normal); "
                  "verify in agent.log: \"MCP server '<name>': registered N tool(s)\"")


async def _run(targets, dry):
    for port, token in targets:
        try:
            await reload_one(port, token, dry)
        except Exception as exc:
            print("    [x] port %d: %s: %s" % (port, type(exc).__name__, exc))


def main():
    ap = argparse.ArgumentParser(description="Reload local Hermes backends (reload.env + reload.mcp)")
    ap.add_argument("--port", type=int, help="target one backend port explicitly")
    ap.add_argument("--dry-run", action="store_true", help="discover only, send nothing")
    args = ap.parse_args()

    if args.port:
        token = probe(args.port)
        if not token:
            sys.exit("port %s: not a hermes headless backend (or unreachable)" % args.port)
        targets = [(args.port, token)]
    else:
        targets = [(p, t) for p in listener_ports() for t in (probe(p),) if t]
        if not targets:
            sys.exit("no hermes headless backend found on loopback listeners")
    asyncio.run(_run(targets, args.dry_run))


if __name__ == "__main__":
    main()
