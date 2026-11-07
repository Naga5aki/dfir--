import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\ForensicsAgent\hermes\bin")
from myos_mount import Myos

PHONE = Path(r"D:\MYOS\Case\2025fic\dev\检材2.tar\data")
WECHAT = PHONE / "MApps" / "Wechat{B556775F-EC07-4F02-82E9-F1FE670253F5}.mfs"
OUT = Path(r"D:\ForensicsAgent\.superpowers\sdd\2026-11-07-hexp-dfir-capability\q6.json")


def q(m, path, sql, rows=40):
    return m.tool("myos-forensics.sqlite_query", {"dbPath": str(path), "sql": sql, "maxRows": rows})


def main() -> None:
    m = Myos()
    found = {}
    try:
        found["base_more"] = q(m, PHONE / "Platform.mfs", "SELECT strInfo, strContent FROM TBL_PR_BASE_INFO LIMIT 80")
        found["wx_acct"] = q(m, WECHAT, "SELECT * FROM TBL_PR_WEIXIN_IM_ACCOUNT LIMIT 5")
        found["mount_phone"] = m.tool("myos-forensics.query_device_mount_path", {"materialId": "51405326-b2d6-404a-8764-f4d50b3caca9"})
        found["mount_pc"] = m.tool("myos-forensics.query_device_mount_path", {"materialId": "352792ec-1ac2-4951-9c98-c1a1451b07e8"})
    finally:
        m.close()
    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT, OUT.stat().st_size)

if __name__ == "__main__":
    main()
