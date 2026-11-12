r"""Plan and (optionally) run keyword searches for computer-forensics questions.

The goal is to turn a question into a short, bounded search plan:
  question -> keywords by type -> suggested MYOS plugin DBs/directories -> commands
  -> optional bounded text search over the mounted evidence.

It never writes to evidence. Search is limited by directory allow-list, file
extensions, max file size, max hits and a wall-clock timeout.

Usage:
  python -I computer_keyword_search.py --question "嫌疑人的备用机号码是多少？" \
    --notes D:\forensics\cases\notes
  python -I computer_keyword_search.py --question "域名dgy02.com曾保存过一个密码" \
    --root "C:/osmap/<id>/Root" --execute --timeout 90 --json
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

STOP_CN = {
    "请分析", "请", "分析", "检材", "回答", "并", "该", "的", "是", "为", "有",
    "什么", "是多少", "多少", "哪个", "哪些", "如何", "怎么", "为什么", "其中",
    "嫌疑人", "电脑", "手机", "系统", "文件", "名称", "号码", "时间", "记录",
    "第一次", "最后一次", "曾", "被", "在", "和", "与", "或", "一个", "这个",
}
STOP_EN = {
    "the", "and", "for", "with", "from", "this", "that", "what", "which",
    "how", "why", "please", "answer", "question", "analysis",
}

ARTIFACT_HINTS = [
    ("boot", re.compile(r"开机|关机|启动|boot|shutdown|wtmp|last", re.I)),
    ("usb", re.compile(r"usb|设备|u盘|移动硬盘", re.I)),
    ("remote", re.compile(r"向日葵|sunlogin|todesk|raylink|远控|远程控制|公网|端口", re.I)),
    ("rdp", re.compile(r"远程连接|远程桌面|\bRDP\b|TerminalServices", re.I)),
    ("bitlocker", re.compile(r"bitlocker|恢复密钥", re.I)),
    ("vhd", re.compile(r"\.vhd\b|\bvhd\b|虚拟磁盘", re.I)),
    ("veracrypt", re.compile(r"veracrypt|加密容器", re.I)),
    ("tor", re.compile(r"torrent|tor browser|洋葱|\.onion", re.I)),
    ("recycle", re.compile(r"删除时间|回收站", re.I)),
    ("mail", re.compile(r"邮件|发件人|附件", re.I)),
    ("gps", re.compile(r"\bgps\b|经纬度|拍摄位置", re.I)),
    ("logon", re.compile(r"登录失败|失败次数|成功登录", re.I)),
    ("browser", re.compile(r"chrome|chromium|浏览器|密码|口令|keyring|钥匙环|login data", re.I)),
    ("wechat", re.compile(r"微信|wechat|weixin", re.I)),
    ("office", re.compile(r"文档|docx|doc|xlsx|pdf|助记词|wallet|md5|哈希", re.I)),
    ("note", re.compile(r"便签|备忘录|note|国庆", re.I)),
    ("audio", re.compile(r"音频|mp3|wav|录音|转写|分段|藏头", re.I)),
    ("vm", re.compile(r"我的测试机|虚拟机|vmware|vmdk|嵌套", re.I)),
    ("phone", re.compile(r"备用机|手机号|电话号码|号码|contact|msisdn", re.I)),
    ("domain", re.compile(r"域名|dns|url|ip|foren6|dgy02", re.I)),
    ("hash", re.compile(r"\b[0-9a-f]{32}\b|\b[0-9a-f]{40}\b|\b[0-9a-f]{64}\b", re.I)),
]

PLUGIN_HINTS = {
    "boot": ["Linux_SystemInfo", "Linux_SystemLog"],
    "usb": ["Linux_UsbInfo", "Win_Usb"],
    "remote": ["Linux_InstallSoftWare", "Win_SystemInfo"],
    "rdp": ["Win_RemoteDesktopInfo"],
    "bitlocker": ["Win_BitlockerRecoveryKey"],
    "recycle": ["Win_RecycleBin"],
    "mail": ["Any_ExchangeMail", "Win_Outlook"],
    "gps": ["Any_ImageExifInfo"],
    "logon": ["Win_SystemInfo", "Win_SystemLog"],
    "browser": ["Any_Chrome", "Any_ChromiumBrowser", "Any_Firefox"],
    "wechat": ["Win_WeChat", "Linux_InstallSoftWare"],
    "office": ["FSData", "Any_OfficeMetaInfo", "Any_FileCategory"],
    "hash": ["FSData"],
    "vm": [],
}

ROUTE_NOTES = {
    "rdp": "Windows「远程连接」先查 Win_RemoteDesktopInfo，不要先翻向日葵日志。",
    "vhd": "盘符查挂载记录或只读挂载副本；不要手解 dynamic VHD BAT。两次无盘符就写 UNKNOWN。",
    "bitlocker": "恢复密钥来自 Win_BitlockerRecoveryKey，不要用密钥文件名或卷 GUID 的末几位。",
    "remote": "仅题面写了向日葵/todesk/远控时才走这条；「成功接收到公网」不是远程桌面的默认答案。",
    "veracrypt": "密码先找模拟器备份里的聊天，不要先破解容器，也不要仿真开机看桌面。",
    "tor": "下载地址先查 Tor 的 places.sqlite，不要只查 Chrome。",
    "logon": "失败次数只数该用户最后一次成功登录之前的失败，不要用最后一次开机代替。",
}

ARTIFACT_KEYWORDS = {
    "boot": ["开机", "关机", "boot", "shutdown", "wtmp", "BOOT_TIME"],
    "usb": ["USB", "设备", "ThinkPlus"],
    "remote": ["向日葵", "sunlogin", "todesk", "远控", "公网"],
    "rdp": ["远程连接", "远程桌面", "RDP"],
    "bitlocker": ["BitLocker", "恢复密钥"],
    "vhd": ["vhd", "虚拟磁盘"],
    "veracrypt": ["VeraCrypt", "加密容器"],
    "tor": ["torrent", "Tor", "onion"],
    "recycle": ["回收站", "删除时间"],
    "mail": ["邮件", "发件人", "附件"],
    "gps": ["GPS", "经纬度"],
    "logon": ["登录失败", "成功登录"],
    "browser": ["Chrome", "Login Data", "keyring", "密码", "dgy02"],
    "wechat": ["微信", "wechat", "版本"],
    "office": ["MD5", "哈希", "助记词", "docx", "wallet"],
    "note": ["便签", "note", "国庆"],
    "audio": ["音频", "MP3", "转写", "分段", "藏头"],
    "vm": ["我的测试机", "vmdk", "虚拟机", "VMware"],
    "phone": ["备用机", "手机号", "电话号码", "号码", "MSISDN"],
    "domain": ["域名", "DNS", "IP", "URL"],
    "hash": [],
}

TEXT_EXT = {
    ".txt", ".log", ".json", ".xml", ".ini", ".conf", ".cfg", ".desktop",
    ".csv", ".md", ".html", ".htm", ".js", ".py", ".sh", ".sql", ".xbel",
    ".yaml", ".yml", ".properties", ".list", ".service",
}
TEXT_NAMES = {
    ".bash_history", ".zsh_history", "status", "wtmp", "btmp", "lastlog",
    # Chrome/SQLite files without a text extension: raw strings are still useful.
    "history", "login data", "local state", "preferences", "web data", "cookies",
}


def extract_keywords(question: str):
    quoted = re.findall(r"[\"“”'‘’]([^\"“”'‘’]{2,60})[\"“”'‘’]", question)
    hashes = re.findall(r"\b[0-9a-fA-F]{32}\b|\b[0-9a-fA-F]{40}\b|\b[0-9a-fA-F]{64}\b", question)
    phones = re.findall(r"(?<!\d)1[3-9]\d{9}(?!\d)", question)
    domains = re.findall(r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b", question)
    versions = re.findall(r"\b\d+(?:\.\d+){1,3}\b", question)
    cn_terms = []
    for chunk in re.split(r"[，。；;：:、,.\s（）()\[\]【】<>《》/|]+", question):
        for term in re.findall(r"[\u4e00-\u9fff]{2,12}", chunk):
            if term not in STOP_CN and len(term) >= 2:
                cn_terms.append(term)
    en_terms = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9_.-]{2,}", question)
                if w.lower() not in STOP_EN]
    # de-duplicate preserving order
    def uniq(xs):
        seen, out = set(), []
        for x in xs:
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out

    keywords = {
        "quoted": uniq(quoted),
        "hash": uniq(hashes),
        "phone": uniq(phones),
        "domain": uniq(domains),
        "version": uniq(versions),
        "cn": uniq(cn_terms),
        "en": uniq(en_terms),
    }
    artifacts = [name for name, rx in ARTIFACT_HINTS if rx.search(question)]
    return keywords, artifacts


def load_plugin_map(notes: Path):
    summary = notes / "device_map.computer.summary.txt"
    if not summary.exists():
        return {}
    plugins = {}
    for line in summary.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"^- ([^|]+)\s*\|\s*([^|]+?\.mfs)", line)
        if m:
            plugins[m.group(1).strip()] = m.group(2).strip()
    return plugins


def suggested_plugins(artifacts, plugin_map):
    wanted = []
    for a in artifacts:
        wanted.extend(PLUGIN_HINTS.get(a, []))
    out = []
    for name in wanted:
        for p, path in plugin_map.items():
            if p.lower() == name.lower() or name.lower() in p.lower():
                out.append({"plugin": p, "dbPath": path})
    return out


def suggested_dirs(root: Path):
    if not root or not root.exists():
        return []
    dirs = []
    p2 = root / "Partition2"
    p4 = root / "Partition4"
    for base in (p4 / "home", p2 / "home"):
        if base.exists():
            for user in base.iterdir():
                if user.is_dir():
                    for sub in ("文档", "桌面", "下载", "图片", ".config/google-chrome",
                                ".local/share/keyrings", ".xwechat"):
                        if (user / sub).exists():
                            dirs.append(str(user / sub))
    for sub in ("var/log", "var/log/sunlogin", "etc", "var/lib/dpkg"):
        if (p2 / sub).exists():
            dirs.append(str(p2 / sub))
    for part in root.iterdir():
        if not part.is_dir():
            continue
        users = part / "Users"
        if not users.exists():
            continue
        for user in users.iterdir():
            if not user.is_dir() or user.name.lower() in {"public", "default", "default user", "all users"}:
                continue
            for sub in ("Documents", "Desktop", "Downloads", "文档", "桌面", "下载"):
                if (user / sub).exists():
                    dirs.append(str(user / sub))
    return dirs


def build_plan(question, notes, root):
    keywords, artifacts = extract_keywords(question)
    plugin_map = load_plugin_map(notes) if notes else {}
    plugins = suggested_plugins(artifacts, plugin_map)
    dirs = suggested_dirs(root) if root else []
    all_kw = []
    for key in ("hash", "phone", "domain", "version", "quoted", "cn", "en"):
        all_kw.extend(keywords.get(key) or [])
    for a in artifacts:
        all_kw.extend(ARTIFACT_KEYWORDS.get(a, []))
    all_kw = list(dict.fromkeys(all_kw))
    sql_templates = []
    for p in plugins:
        sql_templates.append({
            "dbPath": p["dbPath"],
            "sql": "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';",
            "note": "先看表；再按列名写 SELECT ... WHERE lower(<textcol>) LIKE '%kw%' LIMIT 20",
        })
    grep_cmd = ""
    if dirs and all_kw:
        pat = "\\|".join(re.escape(k) for k in all_kw[:8])
        target = " ".join(f"'{d}'" for d in dirs[:12])
        grep_cmd = (
            f"timeout 90 grep -r -l -I -m1 --include='*.txt' --include='*.log' "
            f"--include='*.json' --include='*.xml' --include='*.ini' --include='*.conf' "
            f"--include='*.desktop' --include='*.csv' --include='*.md' "
            f"'{pat}' {target} 2>/dev/null | head -30"
        )
    return {
        "question": question,
        "keywords": keywords,
        "artifacts": artifacts,
        "pluginMapLoaded": bool(plugin_map),
        "suggestedPlugins": plugins,
        "suggestedDirs": dirs,
        "sqlTemplates": sql_templates,
        "grepCommand": grep_cmd,
        "searchKeywords": all_kw,
        "routeNotes": [ROUTE_NOTES[a] for a in artifacts if a in ROUTE_NOTES],
    }


def execute_search(root: Path, keywords, dirs, timeout, max_hits, max_bytes):
    if not keywords:
        return {"hits": [], "note": "no keywords"}
    pats = [k.lower() for k in keywords if len(k) >= 2]
    deadline = time.time() + timeout
    hits, scanned = [], 0
    for d in dirs:
        p = Path(d)
        if not p.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            if time.time() > deadline or len(hits) >= max_hits:
                break
            dirnames[:] = [x for x in dirnames if x.lower() not in
                           {"cachev7", "caches", "cache", "node_modules", ".git", "usr", "lib"}]
            for fn in filenames:
                if time.time() > deadline or len(hits) >= max_hits:
                    break
                f = Path(dirpath) / fn
                try:
                    if not f.is_file() or f.stat().st_size > max_bytes:
                        continue
                except OSError:
                    continue
                low = fn.lower()
                name_hit = next((k for k in pats if k in low), None)
                if name_hit:
                    hits.append({"path": str(f), "where": "filename", "keyword": name_hit})
                    if len(hits) >= max_hits:
                        break
                ext = f.suffix.lower()
                if ext not in TEXT_EXT and fn.lower() not in TEXT_NAMES:
                    continue
                scanned += 1
                try:
                    data = f.read_bytes()
                except OSError:
                    continue
                text = data.decode("utf-8", "ignore").lower()
                for k in pats:
                    idx = text.find(k)
                    if idx >= 0:
                        hits.append({"path": str(f), "where": "content", "keyword": k,
                                     "offset": idx})
                        break
                if len(hits) >= max_hits:
                    break
    return {
        "hits": hits,
        "scannedFiles": scanned,
        "timedOut": time.time() > deadline,
        "maxHits": max_hits,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    ap.add_argument("--notes", default="")
    ap.add_argument("--root", default="")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--max-hits", type=int, default=40)
    ap.add_argument("--max-bytes", type=int, default=20 * 1024 * 1024)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    notes = Path(args.notes) if args.notes else None
    root = Path(args.root) if args.root else None
    plan = build_plan(args.question, notes, root)
    if args.execute:
        if not root:
            print("--execute requires --root", file=sys.stderr)
            return 2
        plan["search"] = execute_search(
            root, plan["searchKeywords"], plan["suggestedDirs"],
            args.timeout, args.max_hits, args.max_bytes,
        )
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print("keywords:", json.dumps(plan["keywords"], ensure_ascii=False))
        print("artifacts:", ",".join(plan["artifacts"]))
        print("plugins:", ", ".join(p["plugin"] for p in plan["suggestedPlugins"]) or "-")
        print("dirs:", len(plan["suggestedDirs"]))
        print("grep:", plan["grepCommand"] or "-")
        if "search" in plan:
            print("hits:", len(plan["search"]["hits"]),
                  "scanned:", plan["search"]["scannedFiles"],
                  "timedOut:", plan["search"]["timedOut"])
            for h in plan["search"]["hits"]:
                print(f"  {h['where']}: {h['keyword']} -> {h['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
