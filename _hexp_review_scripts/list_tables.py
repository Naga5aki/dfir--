import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\ForensicsAgent\hermes\bin")
from myos_mount import Myos

BASE = Path(r"D:\MYOS\Case\2025fic\dev\检材3.E01\data\IntegrateForensics")
DBS = [
    "Linux_SystemInfo",
    "Linux_InstallSoftWare",
    "Linux_UsbInfo",
    "Linux_RecentVisitInfo",
    "Any_Chrome",
    "Win_SunLogin",
    "Win_WeChat",
    "Win_SystemInfo",
]
OUT = Path(r"D:\ForensicsAgent\.superpowers\sdd\2026-11-07-hexp-dfir-capability\tables.txt")

def main() -> None:
    m = Myos()
    lines = []
    try:
        for name in DBS:
            path = str(BASE / f"{name}.mfs")
            res = m.tool(
                "myos-forensics.sqlite_query",
                {
                    "dbPath": path,
                    "sql": "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name",
                    "maxRows": 80,
                },
            )
            lines.append("## " + name)
            lines.append(json.dumps(res, ensure_ascii=False)[:2000])
    finally:
        m.close()
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT, OUT.stat().st_size)

if __name__ == "__main__":
    main()
