#!/usr/bin/env python
"""只读取证数据库的一行命令封装：避免 Windows 下 python -c 的引号地狱。

用法：
  python D:\\ForensicsAgent\\hermes\\bin\\dbq.py "<db 路径>" "SELECT ..." [--limit 50] [--json]
  python D:\\ForensicsAgent\\hermes\\bin\\dbq.py "<db 路径>" --tables
  python D:\\ForensicsAgent\\hermes\\bin\\dbq.py "<db 路径>" --schema <表名>

行为：
  - 强制只读（sqlite URI mode=ro），绝不写证据；
  - 结果以 TSV 打印，首行为列名；--json 输出 JSON 数组；
  - 自动展开 <root> 占位符（读 myos_mount.json 的 rootPath）；
  - 出错时打印结构化 JSON 到 stdout 并以非 0 退出，便于代理判断下一步。
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

STATE_FILE = Path(r"D:\ForensicsAgent\hermes\state\myos_mount.json")


def resolve(path: str) -> str:
    if path.startswith("<root>"):
        try:
            root = json.loads(STATE_FILE.read_text(encoding="utf-8"))["rootPath"]
        except Exception:
            root = ""
        if not root:
            fail("root 未知，先运行 myos_mount.py mount")
        path = root + path[len("<root>"):]
    return str(Path(path))


def fail(msg: str, code: int = 1) -> None:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(code)


def connect(path: str):
    p = Path(path)
    if not p.is_file():
        fail(f"库不存在: {path}")
    uri = "file:///" + path.replace("\\", "/") + "?mode=ro"
    try:
        return sqlite3.connect(uri, uri=True, timeout=5)
    except sqlite3.Error as exc:
        fail(f"打开失败（.mfs 加密库请改用 MCP sqlite_query）: {exc}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("sql", nargs="?")
    ap.add_argument("--tables", action="store_true")
    ap.add_argument("--schema", default="")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    db = resolve(args.db)
    con = connect(db)
    try:
        if args.tables:
            rows = con.execute(
                "select name from sqlite_master where type='table' "
                "and name not like 'sqlite_%' and name not like 'android_%' order by name"
            ).fetchall()
            cols = con.execute(
                "select name from sqlite_master where type='table' "
                "and name not like 'sqlite_%' and name not like 'android_%'"
            ).fetchall()
            out = []
            for name in [r[0] for r in rows]:
                try:
                    n = con.execute(f'select count(*) from "{name}"').fetchone()[0]
                except sqlite3.Error:
                    n = None
                out.append({"table": name, "rows": n})
            print(json.dumps({"ok": True, "db": db, "tables": out}, ensure_ascii=False, indent=1))
            return 0

        sql = args.sql
        if args.schema:
            sql = f'select sql from sqlite_master where name="{args.schema}"'
        if not sql:
            fail("缺少 SQL（或用 --tables / --schema）")

        cur = con.execute(sql)
        rows = cur.fetchmany(args.limit)
        cols = [d[0] for d in cur.description] if cur.description else []
        if args.json:
            print(json.dumps({"ok": True, "columns": cols,
                              "rows": [list(r) for r in rows]}, ensure_ascii=False))
        else:
            print("\t".join(cols))
            for r in rows:
                print("\t".join("" if v is None else str(v) for v in r))
            if len(rows) >= args.limit:
                print(f"-- 仅显示前 {args.limit} 行，用 --limit 调整")
        return 0
    except sqlite3.Error as exc:
        fail(f"SQL 失败: {exc}")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
