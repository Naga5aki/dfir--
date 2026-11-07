import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\ForensicsAgent\hermes\bin")
from myos_mount import Myos

PHONE = Path(r"D:\MYOS\Case\2025fic\dev\检材2.tar\data")
PC = Path(r"D:\MYOS\Case\2025fic\dev\检材3.E01\data\IntegrateForensics")
OUT = Path(r"D:\ForensicsAgent\.superpowers\sdd\2026-11-07-hexp-dfir-capability\q3.json")


def q(m, path, sql, rows=40):
    return m.tool("myos-forensics.sqlite_query", {"dbPath": str(path), "sql": sql, "maxRows": rows})


def main() -> None:
    m = Myos()
    found = {}
    try:
        found["device"] = q(m, PHONE / "Platform.mfs", "SELECT * FROM TBL_PR_DEVICE_INFO LIMIT 5")
        found["phone_base"] = q(m, PHONE / "Platform.mfs", "SELECT * FROM TBL_PR_PHONE_BASEINFO LIMIT 3")
        found["apps"] = q(m, PHONE / "MApps.mfs", "SELECT * FROM TBL_APPDATA_MANAGER LIMIT 40")
        found["auth"] = q(m, PHONE / "MApps.mfs", "SELECT * FROM TBL_PR_APP_AUTHINFO LIMIT 20")
        found["ray"] = q(
            m,
            PC / "Linux_InstallSoftWare.mfs",
            "SELECT PACKAGE_NAME, SOFTWARE_VERSION FROM TBL_AF_LINUXINSTALLSOFTWARE_ST_NORMAL "
            "WHERE PACKAGE_NAME LIKE '%ray%' OR PACKAGE_NAME LIKE '%oray%' OR PACKAGE_NAME LIKE '%ais%' LIMIT 20",
        )
    finally:
        m.close()
    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT, OUT.stat().st_size)

if __name__ == "__main__":
    main()
