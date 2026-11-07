import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\ForensicsAgent\hermes\bin")
from myos_mount import Myos

PHONE = Path(r"D:\MYOS\Case\2025fic\dev\检材2.tar\data")
WECHAT = PHONE / "MApps" / "Wechat{B556775F-EC07-4F02-82E9-F1FE670253F5}.mfs"
OUT = Path(r"D:\ForensicsAgent\.superpowers\sdd\2026-11-07-hexp-dfir-capability\q4.json")


def q(m, path, sql, rows=40):
    return m.tool("myos-forensics.sqlite_query", {"dbPath": str(path), "sql": sql, "maxRows": rows})


def main() -> None:
    m = Myos()
    found = {}
    try:
        found["wechat_tables"] = q(
            m, WECHAT, "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        found["notes_cols"] = q(m, PHONE / "Platform.mfs", "SELECT * FROM TBL_PR_NOTES_INFO LIMIT 1")
        found["base_cols"] = q(m, PHONE / "Platform.mfs", "SELECT * FROM TBL_PR_BASE_INFO LIMIT 3")
    finally:
        m.close()
    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT, OUT.stat().st_size)

if __name__ == "__main__":
    main()
