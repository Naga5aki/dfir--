import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\ForensicsAgent\hermes\bin")
from myos_mount import Myos

PHONE = Path(r"D:\MYOS\Case\2025fic\dev\检材2.tar\data")
PC = Path(r"D:\MYOS\Case\2025fic\dev\检材3.E01\data\IntegrateForensics")
OUT = Path(r"D:\ForensicsAgent\.superpowers\sdd\2026-11-07-hexp-dfir-capability\q2.json")


def q(m, path, sql, rows=30):
    return m.tool(
        "myos-forensics.sqlite_query",
        {"dbPath": str(path), "sql": sql, "maxRows": rows},
    )


def main() -> None:
    m = Myos()
    found = {}
    try:
        for name in ("MApps.mfs", "apklist.mfs", "Platform.mfs"):
            found[name] = q(
                m,
                PHONE / name,
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
            )
        found["soft_hits"] = q(
            m,
            PC / "Linux_InstallSoftWare.mfs",
            "SELECT PACKAGE_NAME, SOFTWARE_VERSION, SOFTWARE_NAME FROM TBL_AF_LINUXINSTALLSOFTWARE_ST_NORMAL "
            "WHERE PACKAGE_NAME LIKE '%wechat%' OR PACKAGE_NAME LIKE '%sunlogin%' OR PACKAGE_NAME LIKE '%todesk%' "
            "OR PACKAGE_NAME LIKE '%raylink%' OR SOFTWARE_NAME LIKE '%微信%' OR SOFTWARE_NAME LIKE '%向日葵%' "
            "OR PACKAGE_NAME LIKE '%oray%' OR SOFTWARE_NAME LIKE '%ToDesk%' LIMIT 40",
        )
    finally:
        m.close()
    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT, OUT.stat().st_size)

if __name__ == "__main__":
    main()
