#!/usr/bin/env python
"""把挂载的手机检材扫成一份"数据源地图"，消灭模型靠猜路径的轮次。

用法：
  python myos_appmap.py                 # 读 myos_mount.json 的 rootPath，增量刷新
  python myos_appmap.py --force         # 强制重扫
  python myos_appmap.py --root <路径>   # 指定 root（默认取挂载状态）

产物：
  D:\\forensics\\cases\\notes\\device_map.json     结构化地图（可被模型直接 read）
  D:\\forensics\\cases\\notes\\device_map.summary.txt  一屏摘要（建议只喂这个）

只读：所有数据库用 sqlite3 URI mode=ro 打开，绝不写入证据目录。
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

STATE_FILE = Path(r"D:\ForensicsAgent\hermes\state\myos_mount.json")
NOTES_DIR = Path(r"D:\forensics\cases\notes")
OUT_JSON = NOTES_DIR / "device_map.json"
OUT_SUM = NOTES_DIR / "device_map.summary.txt"
OUT_COLS = NOTES_DIR / "device_map.columns.json"
LOG_FILE = Path(r"D:\ForensicsAgent\hermes\logs\myos_appmap.log")

SYSTEM_PREFIXES = (
    "android", "com.android", "com.google", "com.miui", "com.xiaomi", "com.qualcomm",
    "com.qti", "com.mediatek", "com.samsung", "org.codeaurora", "com.sec", "com.oppo",
    "com.vivo", "com.hihonor", "com.baidu.mapapi", "com.iflytek", "miui", "com.mi",
)
CHAT_DB_NAMES = ("im.db", "msg_0.db", "msg_1.db")
# 系统包里也常是答案所在地，按白名单额外扫描（不扩大整盘扫描成本）
EXTRA_PKGS = (
    "com.miui.notes",                 # 便签 note.db：本案件 Q2/Q4 的线索就在这
    "com.android.providers.calendar",  # 日历事件（纪念日）
    "com.android.providers.downloads",
    "com.android.providers.media",
    "com.android.providers.telephony",
    "com.miui.gallery",
)
DEADLINE_SECONDS = 180
MAX_PKGS = 80
MAX_TABLES_PER_DB = 24
MAX_COLS_PER_TABLE = 40


def log(msg: str) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def mount_root() -> Path:
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return Path(state.get("rootPath") or "")
    except Exception:
        return Path("")


def detect_layout(root: Path) -> dict:
    """兼容两种解包布局。

    classic：root 下含 data/data，app 私有目录在 root/data/data/<pkg>；
    data：root 本身就是 /data（21:13 这个检材就是这种），app 私有目录在 root/data/<pkg>。
    2026-10-30 实测：按 classic 扫 33C807… 检材得到 0 个包，整张地图失效。
    """
    classic = root / "data" / "data"
    if classic.is_dir():
        return {
            "kind": "classic",
            "data_data": classic,
            "media_root": root / "data" / "media" / "0",
            "app_dirs": [root / "data" / "app", root / "data" / "app" / "asec", root / "system" / "app"],
        }
    return {
        "kind": "data",
        "data_data": root / "data",
        "media_root": root / "media" / "0",
        "app_dirs": [root / "app", root / "app-asec"],
    }


def is_system(pkg: str) -> bool:
    low = pkg.lower()
    return any(low == p or low.startswith(p + ".") for p in SYSTEM_PREFIXES)


def ro_connect(db: Path):
    uri = "file:///" + str(db).replace("\\", "/") + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=2)


def db_tables(db: Path, deadline: float):
    """返回 [{name, rows}]；失败或超时返回 None。"""
    if time.time() > deadline:
        return None
    try:
        con = ro_connect(db)
        try:
            cur = con.execute("select name from sqlite_master where type='table' "
                              "and name not like 'sqlite_%' and name not like 'android_%'")
            names = [r[0] for r in cur.fetchall()][:25]
            out = []
            for name in names:
                if time.time() > deadline:
                    out.append({"name": name, "rows": None})
                    continue
                try:
                    safe = name.replace('"', '""')
                    rows = con.execute(f'select count(*) from "{safe}"').fetchone()[0]
                except Exception:
                    rows = None
                out.append({"name": name, "rows": rows})
            return out
        finally:
            con.close()
    except Exception:
        return None


def db_columns(db: Path, tables, deadline: float):
    """采集列名/类型/3 个样例值，供 evidence_pack 精确定位；加密库打不开返回 None。

    只给脚本读，不要整份喂给模型（device_map.columns.json 常见几十万字节）。
    """
    if not tables or time.time() > deadline:
        return None
    try:
        con = ro_connect(db)
    except Exception:
        return None
    out = {}
    try:
        for t in tables[:MAX_TABLES_PER_DB]:
            if time.time() > deadline:
                break
            name = t.get("name")
            if not name:
                continue
            safe = name.replace('"', '""')
            try:
                info = con.execute('PRAGMA table_info("%s")' % safe).fetchall()
            except Exception:
                continue
            cols = []
            for col in info[:MAX_COLS_PER_TABLE]:
                cname = col[1]
                if not cname:
                    continue
                csafe = cname.replace('"', '""')
                samples = []
                try:
                    rows = con.execute(
                        'select cast("%s" as text) from "%s" '
                        'where "%s" is not null and length(cast("%s" as text)) between 1 and 160 '
                        'limit 3' % (csafe, safe, csafe, csafe)).fetchall()
                    for (v,) in rows:
                        v = " ".join(str(v).split())
                        if v:
                            samples.append(v[:40])
                except Exception:
                    pass
                cols.append({"name": cname, "type": str(col[2] or ""), "samples": samples})
            if cols:
                out[name] = {"rows": t.get("rows"), "columns": cols}
        return out
    finally:
        try:
            con.close()
        except Exception:
            pass


def dir_summary(path: Path, limit: int = 60):
    """列出子目录名与条目数（不递归），失败返回 []。"""
    out = []
    try:
        for i, entry in enumerate(os.scandir(path)):
            if i >= limit:
                break
            try:
                if entry.is_dir():
                    try:
                        count = sum(1 for _ in os.scandir(entry.path))
                    except OSError:
                        count = None
                    out.append({"name": entry.name, "children": count})
            except OSError:
                continue
    except OSError:
        pass
    return out


def scan_pkg(pkg_dir: Path, deadline: float, cols_out: dict) -> dict:
    pkg = pkg_dir.name
    info = {"pkg": pkg, "top_dirs": [], "databases": [], "mmkv": [], "files_dirs": [],
            "shared_prefs": 0, "chat_dbs": [], "notes": []}

    info["top_dirs"] = dir_summary(pkg_dir, limit=30)

    dbs_dir = pkg_dir / "databases"
    if dbs_dir.is_dir():
        try:
            for entry in sorted(os.scandir(dbs_dir), key=lambda e: e.name):
                if not entry.is_file():
                    continue
                name = entry.name
                if name.endswith("-wal") or name.endswith("-shm"):
                    continue
                if not (name.endswith(".db") or name.endswith(".sqlite") or name.endswith(".db3")):
                    continue
                item = {"file": str(Path(entry.path)), "size_kb": round(entry.stat().st_size / 1024)}
                tables = db_tables(Path(entry.path), deadline)
                if tables is not None:
                    item["tables"] = tables
                    schema = db_columns(Path(entry.path), tables, deadline)
                    if schema:
                        cols_out[str(Path(entry.path))] = schema
                info["databases"].append(item)
                if len(info["databases"]) >= 30:
                    break
        except OSError:
            pass

    files_dir = pkg_dir / "files"
    if files_dir.is_dir():
        info["files_dirs"] = dir_summary(files_dir, limit=40)
        draft_like = [d for d in info["files_dirs"]
                      if d["name"] in ("draft", "drafts", "newdrafts", "tmp", "draft_box")]
        if draft_like:
            info["notes"].append("files 下草稿类目录名: " + ", ".join(d["name"] for d in draft_like) +
                                 "（draft 常见为占位图，工程本体要看 newdrafts 等目录）")
        mmkv_dir = files_dir / "mmkv"
        if mmkv_dir.is_dir():
            try:
                info["mmkv"] = [e.name for e in os.scandir(mmkv_dir) if e.is_file()][:20]
            except OSError:
                pass
        # 聊天/IM 子目录：<uid>_<hex> 下含 im.db / msg_0.db
        for sub in info["files_dirs"][:25]:
            sub_path = files_dir / sub["name"]
            if not sub_path.is_dir():
                continue
            try:
                names = {e.name for e in os.scandir(sub_path) if e.is_file()}
            except OSError:
                continue
            hit = sorted(names.intersection(CHAT_DB_NAMES))
            if hit:
                info["chat_dbs"].append({"dir": str(sub_path), "files": hit})

    prefs_dir = pkg_dir / "shared_prefs"
    if prefs_dir.is_dir():
        try:
            info["shared_prefs"] = sum(1 for _ in os.scandir(prefs_dir))
        except OSError:
            pass

    # 已知易错点提示（来自本案件实战）
    if pkg == "com.lemon.lv":
        info["notes"].append("剪映工程：files\\newdrafts 下的 UUID 目录才是工程本体；files\\draft 只是占位图、tmp 是缓存")
        if (files_dir / "home_feed_cache").is_dir():
            info["notes"].append("手机号线索：files\\home_feed_cache\\key_*.json 的 web_uid 常为「手机号+4位随机数」")
    if pkg == "com.aijiami.cn":
        info["notes"].append("加固/加密工具：用户数据可能为空，包名本身就是答案线索；算法需 jadx 反编译 EncryptionUtils")
    if pkg == "com.dbbjt.phonelive":
        info["notes"].append("搜索关键词在 files\\mmkv\\dbb_ugc_editor_home_history_biz 的 _search_history_info_key；dbb_search_tab_key 只是页签")
    if info["chat_dbs"]:
        info["notes"].append("聊天库在 files/<uid>_<hex>/ 下；message 表 status=3 为发送失败、2 为正常")
    return info


def system_health(data_data: Path) -> dict:
    """系统层"有没有料"先体检：手机号/短信类题目最大的时间浪费是反复试空库。

    只数行数（0 行 = 该源在本检材里不可用），不读内容。data_data 由 detect_layout 给出。
    """
    items = {
        "contacts": ("com.android.providers.contacts/databases/contacts2.db", "raw_contacts"),
        "calllog": ("com.android.providers.contacts/databases/calllog.db", "calls"),
        "sms": ("com.android.providers.telephony/databases/mmssms.db", "sms"),
    }
    out = {}
    for key, (rel, table) in items.items():
        db = data_data / rel
        rows = None
        if db.is_file():
            try:
                con = ro_connect(db)
                try:
                    rows = con.execute('select count(*) from "%s"' % table).fetchone()[0]
                except Exception:
                    rows = None
                finally:
                    con.close()
            except Exception:
                rows = None
        out[key] = rows
    return out


def scan(root: Path, deadline: float):
    layout = detect_layout(root)
    data_data = layout["data_data"]
    media_root = layout["media_root"]
    cols_out = {}
    map_data = {"root": str(root), "layout": layout["kind"], "scanned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "packages": [], "system_packages": [], "media": {}, "apk_files": [],
                "wifi_config": None, "summary": {}}

    pkgs = []
    if data_data.is_dir():
        try:
            pkgs = sorted([e for e in os.scandir(data_data) if e.is_dir()], key=lambda e: e.name)
        except OSError:
            pass

    third = []
    for entry in pkgs:
        if is_system(entry.name):
            map_data["system_packages"].append(entry.name)
        else:
            third.append(entry)

    for entry in third[:MAX_PKGS]:
        if time.time() > deadline:
            map_data["summary"]["truncated"] = True
            break
        map_data["packages"].append(scan_pkg(Path(entry.path), deadline, cols_out))
    if len(third) > MAX_PKGS:
        map_data["summary"]["truncated"] = True

    # 系统包里也有"料"：小米便签 note.db（本案件 Q2 电脑密码/Q4 秘钥环就在这）、日历、下载
    extra = []
    for name in EXTRA_PKGS:
        pkg_dir = data_data / name
        if not pkg_dir.is_dir():
            continue
        try:
            info = scan_pkg(pkg_dir, deadline, cols_out)
        except Exception:
            continue
        info["system"] = True
        extra.append(info)
    map_data["packages"].extend(extra)

    if media_root.is_dir():
        for d in dir_summary(media_root, limit=20):
            map_data["media"][d["name"]] = d["children"]
        # 顶层散落文件（APK / txt / 备份）常是题干线索来源，只列名字与大小，不读内容
        try:
            map_data["media_files"] = sorted(
                "%s (%dKB)" % (e.name, round(e.stat().st_size / 1024))
                for e in os.scandir(media_root) if e.is_file())
        except OSError:
            pass
        backup_dir = media_root / "backup"
        if backup_dir.is_dir():
            try:
                map_data["backup_files"] = sorted(e.name for e in os.scandir(backup_dir) if e.is_file())
            except OSError:
                pass

    # APK 清单（识别加密工具/第三方应用）
    for base in layout["app_dirs"]:
        if not base.is_dir():
            continue
        try:
            for entry in os.scandir(base):
                if entry.is_file() and entry.name.endswith(".apk"):
                    map_data["apk_files"].append(entry.path)
                elif entry.is_dir():
                    for sub in os.scandir(entry.path):
                        if sub.is_file() and sub.name.endswith(".apk"):
                            map_data["apk_files"].append(sub.path)
                if len(map_data["apk_files"]) >= 150:
                    break
        except OSError:
            continue

    wifi = (root / "data" / "misc" if layout["kind"] == "classic" else root / "misc") \
        / "apexdata" / "com.android.wifi" / "WifiConfigStore.xml"
    map_data["wifi_config"] = str(wifi) if wifi.is_file() else None

    chat_pkgs = [p["pkg"] for p in map_data["packages"] if p["chat_dbs"]]
    db_total = sum(len(p["databases"]) for p in map_data["packages"])
    map_data["system_health"] = system_health(data_data)
    map_data["summary"] = {
        "mount_root": str(root),
        "layout": layout["kind"],
        "third_party_count": len(map_data["packages"]),
        "system_package_count": len(map_data["system_packages"]),
        "databases": db_total,
        "columns_dbs": len(cols_out),
        "columns_total": sum(len(t["columns"]) for tables in cols_out.values() for t in tables.values()),
        "chat_packages": chat_pkgs,
        "media_dirs": map_data["media"],
        "apk_count": len(map_data["apk_files"]),
        "system_health": map_data["system_health"],
    }
    return map_data, cols_out


def write_summary(map_data: dict) -> None:
    s = map_data["summary"]
    health = s.get("system_health") or {}
    def _h(k):
        v = health.get(k)
        return "缺库" if v is None else "%d 行" % v
    lines = [
        "ROOT = %s" % s["mount_root"],
        "解包布局：%s（%s）" % (
            s.get("layout", "?"),
            "root/data/data/<pkg>" if s.get("layout") == "classic" else "root 即 /data，app 私有目录在 root/data/<pkg>"),
        "第三方包 %d 个，系统包 %d 个，明文库 %d 个；列名地图 %d 库 / %d 列（用 evidence_pack.py 取，不要整份读）" % (
            s["third_party_count"], s["system_package_count"], s["databases"],
            s.get("columns_dbs", 0), s.get("columns_total", 0)),
        "数据源体检：联系人 %s / 通话 %s / 短信 %s（0 行的源本检材不可用，不要再花轮次）" % (
            _h("contacts"), _h("calllog"), _h("sms")),
        "含聊天库的包: %s" % (", ".join(s["chat_packages"]) or "无"),
        "媒体目录: %s" % (", ".join("%s=%s" % (k, v) for k, v in s["media_dirs"].items()) or "无"),
        "媒体根目录文件: %s" % (", ".join(map_data.get("media_files") or []) or "无"),
    ]
    if map_data.get("backup_files"):
        lines.append("backup 目录: %s" % ", ".join(map_data["backup_files"]))
    lines += [
        "",
        "== 线索速查（先按表取数；体检为 0 行的源直接跳过）==",
        "- 手机号（含 135 号段）：系统库不可用时查 com.lemon.lv files\\home_feed_cache\\key_*.json 的 web_uid=手机号+随机位，取前 11 位；再查各 App mmkv/shared_prefs",
        "- 聊天条数/发送失败：含聊天库的包 files/<uid>_<hex>/msg_0.db message 表（status=3 发送失败）",
        "- 加密算法/密码：jadx 反编译对应 APK 的 EncryptionUtils；音频口述需 ASR",
        "- 剪映工程数：com.lemon.lv files\\newdrafts 下 UUID 目录；draft 是占位图不计",
        "",
        "== 第三方包（包名 | 库数 | 关键子目录）==",
    ]
    for p in map_data["packages"]:
        dbs = len(p["databases"])
        dirs = ", ".join("%s(%s)" % (d["name"], d["children"]) for d in p["files_dirs"][:6])
        if not dirs:
            dirs = ", ".join("%s(%s)" % (d["name"], d["children"]) for d in p["top_dirs"][:6])
        lines.append("%s | db=%d | dirs: %s" % (p["pkg"], dbs, dirs or "-"))
        for note in p["notes"]:
            lines.append("    ! %s" % note)
    OUT_SUM.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    root = Path(args.root) if args.root else mount_root()
    if not root or not root.is_dir():
        print("root 不可用，先运行 myos_mount.py mount", file=sys.stderr)
        return 2

    if not args.force and OUT_JSON.is_file():
        try:
            old = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            if old.get("root") == str(root):
                print("复用已有 device_map.json（--force 可重扫）")
                return 0
        except Exception:
            pass

    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    map_data, cols_out = scan(root, t0 + DEADLINE_SECONDS)
    OUT_JSON.write_text(json.dumps(map_data, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_COLS.write_text(json.dumps(
        {"root": str(root), "scanned_at": map_data["scanned_at"], "dbs": cols_out},
        ensure_ascii=False), encoding="utf-8")
    write_summary(map_data)
    log("scanned root=%s packages=%d db=%d in %.1fs" % (
        root, len(map_data["packages"]), map_data["summary"]["databases"], time.time() - t0))
    print("device_map: %d 个第三方包 / %d 个明文库 / %.1fs" % (
        len(map_data["packages"]), map_data["summary"]["databases"], time.time() - t0))
    print("summary -> %s" % OUT_SUM)
    return 0


if __name__ == "__main__":
    sys.exit(main())
