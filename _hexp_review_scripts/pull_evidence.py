import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\ForensicsAgent\hermes\bin")
from myos_mount import Myos

OUT = Path(r"D:\ForensicsAgent\.superpowers\sdd\2026-11-07-hexp-dfir-capability\evidence.json")
PC = Path(r"D:\MYOS\Case\2025fic\dev\检材3.E01\data\IntegrateForensics")
PHONE_FS = r"D:\MYOS\Case\2025fic\dev\检材2.tar\data\FSData.mfs"

QUERIES = [
    ("boot", PC / "Linux_SystemInfo.mfs", "SELECT * FROM TBL_AF_LINUXSYSINFO_ST_BOOTSHUTDOWN LIMIT 20"),
    ("sysinfo", PC / "Linux_SystemInfo.mfs", "SELECT * FROM TBL_AF_LINUXSYSINFO_ST_SYSTEMINFO LIMIT 5"),
    ("soft", PC / "Linux_InstallSoftWare.mfs", "SELECT * FROM TBL_AF_LINUXINSTALLSOFTWARE_ST_NORMAL LIMIT 5"),
    ("usb", PC / "Linux_UsbInfo.mfs", "SELECT * FROM TBL_AF_LINUXUSB_ST_USBINFO LIMIT 20"),
    ("chrome_login", PC / "Any_Chrome.mfs", "SELECT * FROM TBL_AF_CHROME_WEB_LOGINDATA LIMIT 5"),
    ("sunlogin", PC / "Win_SunLogin.mfs", "SELECT * FROM TBL_SUNLOGIN_HISTORYLOG LIMIT 10"),
    ("wechat_acct", PC / "Win_WeChat.mfs", "SELECT * FROM TBL_AF_WECHAT_IM_ACCOUNT LIMIT 10"),
]


def shrink(obj, limit=400):
    if isinstance(obj, str) and len(obj) > limit:
        return obj[:limit] + "...<cut>"
    if isinstance(obj, list):
        return [shrink(x, limit) for x in obj[:30]]
    if isinstance(obj, dict):
        return {k: shrink(v, limit) for k, v in obj.items()}
    return obj


def main() -> None:
    m = Myos()
    found = {}
    try:
        info = m.tool("myos-forensics.query_device_info", {"dbPath": PHONE_FS, "materialId": "51405326-b2d6-404a-8764-f4d50b3caca9"})
        found["phone_device"] = shrink(info, 500)
        for key, path, sql in QUERIES:
            res = m.tool("myos-forensics.sqlite_query", {"dbPath": str(path), "sql": sql, "maxRows": 20})
            found[key] = shrink(res, 300)
    finally:
        m.close()
    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT, OUT.stat().st_size)

if __name__ == "__main__":
    main()
