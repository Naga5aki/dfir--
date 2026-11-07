import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\ForensicsAgent\hermes\bin")
from myos_mount import Myos

PHONE = Path(r"D:\MYOS\Case\2025fic\dev\检材2.tar\data")
WECHAT = PHONE / "MApps" / "Wechat{B556775F-EC07-4F02-82E9-F1FE670253F5}.mfs"
OUT = Path(r"D:\ForensicsAgent\.superpowers\sdd\2026-11-07-hexp-dfir-capability\q5.json")


def q(m, path, sql, rows=20):
    return m.tool("myos-forensics.sqlite_query", {"dbPath": str(path), "sql": sql, "maxRows": rows})


def main() -> None:
    m = Myos()
    found = {}
    try:
        found["notes"] = q(m, PHONE / "Platform.mfs", "SELECT strTitle, strSummary, strCreated, strAuthor, strContents, strPath FROM TBL_PR_NOTES_INFO")
        found["base"] = q(m, PHONE / "Platform.mfs", "SELECT strInfo, strContent FROM TBL_PR_BASE_INFO")
        found["acct_tables"] = q(
            m,
            WECHAT,
            "SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%ACCOUNT%' OR name LIKE '%USER%' OR name LIKE '%UIN%' OR name LIKE '%DB%')",
        )
    finally:
        m.close()
    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT, OUT.stat().st_size)

if __name__ == "__main__":
    main()
