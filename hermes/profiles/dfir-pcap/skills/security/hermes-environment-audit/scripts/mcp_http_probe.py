#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地 HTTP MCP 独立探针（hermes-environment-audit 技能支持文件）。

不经 Hermes，直接对本机 HTTP MCP 端点做 initialize → notifications/initialized
→ tools/list，核实"端点在线、token 有效、工具数量与名单"（盘点/恢复后的独立证据）。

用法：
    python mcp_http_probe.py http://127.0.0.1:41215/mcp --env-key MCP_CTF_MISC_ARSENAL_API_KEY
    python mcp_http_probe.py <endpoint>              # 无认证服务器
    python mcp_http_probe.py <endpoint> --names none # 只看计数

说明：
- token 默认从 Hermes .env（$HERMES_HOME/.env 或 %LOCALAPPDATA%/hermes/.env）按 key 名读取；
  从不回显 token。
- 绕过系统代理直连本机（ProxyHandler({})）；JSON 与 SSE 应答均支持。
- 退出码：0 成功；2 token 缺失；3 连接或协议失败。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def hermes_home() -> str:
    home = (os.environ.get("HERMES_HOME") or "").strip()
    if home:
        return home
    local = (os.environ.get("LOCALAPPDATA") or "").strip()
    if local:
        return os.path.join(local, "hermes")
    return os.path.expanduser("~/.hermes")


def read_env_key(key: str) -> str:
    path = os.path.join(hermes_home(), ".env")
    if os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def post(opener, endpoint, token, payload, session=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if session:
        headers["Mcp-Session-Id"] = session
    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"),
                                 method="POST", headers=headers)
    resp = opener.open(req, timeout=15)
    raw = resp.read().decode("utf-8", "replace")
    sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
    if raw[:5] == "event" or "data:" in raw[:64]:
        for ln in raw.splitlines():
            if ln.startswith("data:"):
                raw = ln[5:].strip()
                break
    return json.loads(raw), sid


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe a local HTTP MCP endpoint (initialize + tools/list).")
    ap.add_argument("endpoint", help="e.g. http://127.0.0.1:41215/mcp")
    ap.add_argument("--env-key", default="", help="Key name in Hermes .env holding the Bearer token")
    ap.add_argument("--token-stdin", action="store_true", help="Read token from stdin instead of .env")
    ap.add_argument("--names", choices=["all", "count", "none"], default="all")
    args = ap.parse_args()

    token = ""
    if args.token_stdin:
        token = sys.stdin.read().strip()
    elif args.env_key:
        token = read_env_key(args.env_key)
        if not token:
            print(f"NO TOKEN: '{args.env_key}' not found in {os.path.join(hermes_home(), '.env')}", file=sys.stderr)
            return 2

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        init, sid = post(opener, args.endpoint, token, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "hermes-mcp-probe", "version": "1.0"}},
        })
    except urllib.error.HTTPError as exc:
        hint = "token invalid/missing" if exc.code in (401, 403) else str(exc.reason)
        print(f"HTTP {exc.code}: endpoint reachable but rejected initialize ({hint})", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"CONNECT FAILED ({exc!r}): endpoint offline? Start the backing program first.", file=sys.stderr)
        return 3

    result = (init or {}).get("result") or {}
    srv = result.get("serverInfo") or {}
    proto = result.get("protocolVersion", "")
    print(f"SERVER: {json.dumps(srv, ensure_ascii=False)} protocol={proto} session={'yes' if sid else 'no'}")

    try:  # notifications/initialized（失败可忽略）
        post(opener, args.endpoint, token,
             {"jsonrpc": "2.0", "method": "notifications/initialized"}, session=sid)
    except Exception:
        pass

    try:
        lst, _ = post(opener, args.endpoint, token,
                      {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, session=sid)
    except Exception as exc:
        print(f"tools/list FAILED: {exc!r}", file=sys.stderr)
        return 3

    tools = ((lst or {}).get("result") or {}).get("tools") or []
    print(f"TOOL_COUNT: {len(tools)}")
    if args.names == "all":
        for t in tools:
            desc = (t.get("description") or "").split("\n")[0][:88]
            print(f"{t.get('name')} :: {desc}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
