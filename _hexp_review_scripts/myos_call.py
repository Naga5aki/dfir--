"""Talk to the local MYOS MCP server over stdio. Prints tool results, never tokens."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

EXE = r"D:\MYOS\Client\tools\mcp\myos_mcp_server.exe"


class Mcp:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            [EXE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.n = 0

    def send(self, method: str, params: dict | None = None, note: bool = False) -> dict | None:
        self.n += 1
        msg = {"jsonrpc": "2.0", "method": method}
        if not note:
            msg["id"] = self.n
        if params is not None:
            msg["params"] = params
        raw = json.dumps(msg, ensure_ascii=False)
        assert self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(f"Content-Length: {len(raw.encode('utf-8'))}\r\n\r\n{raw}")
        self.proc.stdin.flush()
        if note:
            return None
        headers = {}
        while True:
            line = self.proc.stdout.readline()
            if line == "":
                err = self.proc.stderr.read() if self.proc.stderr else ""
                raise SystemExit(f"mcp closed: {err[:400]}")
            line = line.strip()
            if not line:
                break
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.lower()] = v.strip()
        length = int(headers.get("content-length", "0"))
        body = self.proc.stdout.read(length)
        return json.loads(body)


def main() -> int:
    mcp = Mcp()
    init = mcp.send(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "fic-myos", "version": "0"},
        },
    )
    print("init", "result" in (init or {}), file=sys.stderr)
    mcp.send("notifications/initialized", note=True)
    name = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    result = mcp.send("tools/call", {"name": name, "arguments": args})
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if out:
        out.write_text(text, encoding="utf-8")
        print(out, len(text))
    else:
        print(text[:6000])
    mcp.proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
