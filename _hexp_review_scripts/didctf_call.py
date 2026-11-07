"""Call DIDCTF arena MCP without printing the bearer token."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ENV = Path(r"D:\ForensicsAgent\hermes\profiles\dfir-myos\.env")
URL = "https://forensics.didctf.com/api/arena/mcp"


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DIDCTF_AGENT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("token missing")


def post(payload: dict, opener) -> tuple[dict, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {load_token()}",
        },
        method="POST",
    )
    with opener.open(req, timeout=60) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        status = resp.status
    print("status", status, "bytes", len(body), file=sys.stderr)
    if not body.strip():
        return {"_empty": True, "_status": status}, body
    if "data:" in body and not body.lstrip().startswith("{"):
        chunks = [line[5:].strip() for line in body.splitlines() if line.startswith("data:")]
        body = chunks[-1] if chunks else ""
        if not body:
            return {"_empty": True, "_status": status}, ""
    try:
        return json.loads(body), body
    except json.JSONDecodeError:
        return {"_raw": body[:200], "_status": status}, body


def main() -> int:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    init, _ = post(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "fic-check", "version": "0"},
            },
        },
        opener,
    )
    print("init_ok", "result" in init, file=sys.stderr)
    if "error" in init:
        print(json.dumps(init["error"], ensure_ascii=False))
        return 1
    post({"jsonrpc": "2.0", "method": "notifications/initialized"}, opener)
    if sys.argv[1] == "--batch":
        calls = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        out_path = Path(sys.argv[3])
        collected = []
        for item in calls:
            result, _ = post(
                {
                    "jsonrpc": "2.0",
                    "id": item["id"],
                    "method": "tools/call",
                    "params": {"name": item["name"], "arguments": item.get("arguments") or {}},
                },
                opener,
            )
            collected.append({"id": item["id"], "result": result})
        out_path.write_text(json.dumps(collected, ensure_ascii=False), encoding="utf-8")
        print(out_path, len(collected))
        return 0
    name = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    result, _ = post(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": name, "arguments": args}},
        opener,
    )
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if out:
        out.write_text(text, encoding="utf-8")
        print(out, len(text))
    else:
        print(text[:8000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
