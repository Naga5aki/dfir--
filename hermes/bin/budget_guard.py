#!/usr/bin/env python
"""时间预算收口兜底：hermes 退出后检查本轮是否产出了 pending 文件。

用法：
  budget_guard.py begin --profile dfir-max
  budget_guard.py end   --profile dfir-max [--min-seconds 300] [--dry-run]

begin：记录 notes 目录下 pending-*.md 的基线（mtime + size）。
end  ：若没有任何 pending-*.md 新增或更新，则向 notes/_timeout.log 追加一行 TIMEOUT。
       耗时低于 --min-seconds 的短会话（--version、快速问答）不记，避免噪声。
失败一律静默（退出码 0），不得影响 Hermes 启动。
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

NOTES_DIR = Path(r"D:\forensics\cases\notes")
STATE_DIR = Path(r"D:\ForensicsAgent\hermes\state")
LOG_FILE = Path(r"D:\ForensicsAgent\hermes\logs\budget_guard.log")
TIMEOUT_LOG = NOTES_DIR / "_timeout.log"


def log(msg: str) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {msg}\n")
    except Exception:
        pass


def state_path(profile: str) -> Path:
    safe = "".join(c for c in profile if c.isalnum() or c in "-_") or "default"
    return STATE_DIR / f"budget_guard_{safe}.json"


def snapshot() -> dict:
    out = {}
    if not NOTES_DIR.is_dir():
        return out
    for p in NOTES_DIR.glob("pending-*.md"):
        try:
            st = p.stat()
            out[p.name] = [int(st.st_mtime), st.st_size]
        except OSError:
            continue
    return out


def record_timeout(profile: str, elapsed: int, reason: str, dry_run: bool = False) -> None:
    line = (
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {profile} | "
        f"elapsed={elapsed}s | TIMEOUT {reason}"
    )
    if dry_run:
        print(line)
        return
    try:
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        with TIMEOUT_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        log(f"已记 TIMEOUT profile={profile} elapsed={elapsed}s {reason}")
    except Exception as exc:
        log(f"写 TIMEOUT 失败 {exc}")


def do_begin(profile: str, min_seconds: int) -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    sp = state_path(profile)
    # 上一轮 begin 之后没有正常 end（关窗口、双击 Ctrl+C、被杀进程）：补记后覆盖
    if sp.is_file():
        try:
            prev = json.loads(sp.read_text(encoding="utf-8-sig"))
            prev_elapsed = int(time.time() - float(prev.get("start", time.time())))
            if prev_elapsed >= min_seconds:
                record_timeout(profile, prev_elapsed, "上一轮未执行收口检查（异常终止）")
            else:
                log(f"begin: 清理残留基线 profile={profile} elapsed={prev_elapsed}s")
        except Exception as exc:
            log(f"begin: 残留基线无法解析，忽略 {exc}")
    data = {"profile": profile, "start": time.time(), "files": snapshot()}
    sp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return 0


def do_end(profile: str, min_seconds: int, dry_run: bool) -> int:
    sp = state_path(profile)
    if not sp.is_file():
        log(f"end: 缺少基线状态文件，跳过 profile={profile}")
        return 0
    try:
        data = json.loads(sp.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        log(f"end: 状态文件解析失败 {exc}")
        return 0

    elapsed = int(time.time() - float(data.get("start", time.time())))
    before = {k: tuple(v) for k, v in (data.get("files") or {}).items()}
    after = {k: tuple(v) for k, v in snapshot().items()}

    changed = [name for name, sig in after.items() if before.get(name) != sig]
    try:
        sp.unlink()
    except OSError:
        pass

    if changed:
        log(f"end: 正常收口 profile={profile} elapsed={elapsed}s pending={changed}")
        return 0

    if elapsed < min_seconds:
        log(f"end: 短会话不记 TIMEOUT profile={profile} elapsed={elapsed}s < {min_seconds}s")
        return 0

    record_timeout(profile, elapsed, "未收口（本轮无 pending-*.md 新增或更新）", dry_run)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("begin", "end"):
        p = sub.add_parser(name)
        p.add_argument("--profile", required=True)
        p.add_argument("--min-seconds", type=int, default=300)
        if name == "end":
            p.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.cmd == "begin":
        return do_begin(args.profile, args.min_seconds)
    return do_end(args.profile, args.min_seconds, args.dry_run)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # 绝不打断 Hermes
        log(f"fatal: {exc}")
        sys.exit(0)
