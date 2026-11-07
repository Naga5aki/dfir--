#!/usr/bin/env python
"""按题型预取"证据包"：候选值 + 取数入口，把探索从模型搬到脚本。

为什么：本地模型每轮 10-85s，一题 12 轮探索就烧掉 10 分钟且常常 0 收口。
        预取一次只需 0.1-2s，模型改成"读候选 → 复核 → 落盘"。

用法：
  python evidence_pack.py --q 3 --text "嫌疑人接头暗号是什么？"   # 自动判题型并写 notes/evidence-q3.txt
  python evidence_pack.py --type wechat_uin
  python evidence_pack.py --list

只读：sqlite 一律 mode=ro，文件只读；绝不写检材目录。
产物：D:\\forensics\\cases\\notes\\evidence-q<N>.txt（同时打印到 stdout）。
"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

NOTES_DIR = Path(r"D:\forensics\cases\notes")
MAP_JSON = NOTES_DIR / "device_map.json"
COLS_JSON = NOTES_DIR / "device_map.columns.json"
DEADLINE_SECONDS = 45
MAX_QUERIES = 600
MAX_FILE_BYTES = 1_500_000

STOPWORDS = (
    "请分析", "检材", "手机", "回答", "什么", "是什么", "嫌疑人", "该", "对应", "多少",
    "文件", "名称", "为", "的", "共有", "其中", "号码", "请", "并", "该手机",
)

# SDK 遥测/广告配置文件：里面全是时间戳与 32 位哈希，是各题型最大的噪声源（实测 Q5/Q8 都被它压过正解）
SDK_NOISE = (
    "umeng", "firebaseheartbeat", "mi_stat", "statstorage", "pangle", "qq.e",
    "gdt", "turingfd", "lcdpr", "/host/", "wlogin_device_info",
)

# 题型模板：patterns 用于判题，kw 用于 SQL LIKE / 文件检索，extract 抓答案候选
TEMPLATES = {
    "device_name": {
        "title": "设备名称 device_name",
        "patterns": [r"device[_\s-]?name", r"设备名", r"手机型号", r"设备型号"],
        "kw": ["device_name", "ro.product.model", "market_name", "DEVICE_NAME"],
        "extract": [
            r"device_name[\"']?\s*[=:]\s*[\"']?([^\"'<>,;}\s]{2,40})",
            r"(?:ro\.product\.model|market_name|ProductModel)[\"']?\s*[=:]\s*[\"']?([^\"'<>,;}\s]{2,40})",
        ],
        "files": ["settings_ssaid.xml", "device_name", "build.prop", "device_config.xml"],
        "root_files": ["property/persistent_properties", "system/users/0/settings_ssaid.xml"],
        "props": ["persist.sys.device_name", "ro.product.model", "ro.product.marketname"],
        "hints": [
            "settings_ssaid.xml 只有 ssaid，不含 device_name；本检材实测答案在 property/persistent_properties 的 persist.sys.device_name（protobuf，按字节读）",
            "小米/红米机型 market_name 比 model 可读，答案行按题面要求的原始值写",
        ],
    },
    "pc_password": {
        "title": "开机密码 / 登录密码",
        "patterns": [r"开机密码", r"pc.{0,4}密码", r"登录密码", r"电脑密码"],
        "kw": ["开机密码", "登录密码", "密码", "password", "passcode"],
        "extract": [
            r"(?:开机密码|登录密码|密码|password|passcode)[\"']?\s*[=:：是为]+\s*[\"']?([^\"'<>\s，。；,}]{3,40})",
            r"(?:lock_password|unlock_password)[=:]\s*([^\s\"<]{3,40})",
        ],
        "hints": [
            "PC 密码通常出现在聊天文本里（如「我电脑密码是 xxx」），先查微信/QQ 聊天库文本列",
            "其次看小米便签 com.miui.notes/databases/note.db 的 plain_text / snippet（本案件 Q2 的「电脑密码」就记在便签里）",
            "再查 shared_prefs / android.provider.settings.secure 的 lock_password",
        ],
    },
    "secret_code": {
        "title": "接头暗号",
        "patterns": [r"接头暗号", r"暗号", r"暗语"],
        "kw": ["接头暗号", "暗号", "口令", "暗语"],
        "extract": [
            r"(?:接头暗号|暗号|口令|暗语)[\"']?\s*[=:：是为]+\s*[\"']?([^\"'<>\s，。；,}]{2,30})",
        ],
        "hints": [
            "暗号多在聊天文本里，形如「暗号：天王盖地虎」「接头用××××」",
            "若命中多条，按「暗号」字样紧邻的值优先，其次是对话里双方确认的那条",
        ],
    },
    "keyring": {
        "title": "秘钥环 / 密钥环",
        "patterns": [r"秘钥环", r"密钥环", r"keyring"],
        "kw": ["秘钥环", "密钥环", "秘钥", "密钥", "keyring"],
        "extract": [
            r"(?:秘钥环|密钥环|keyring)[\s：:=是为]*([A-Za-z0-9+/=_\-]{4,60})",
            r"(?:秘钥|密钥)[\"']?\s*[=:：]\s*[\"']?([^\"'<>\s，。；}]{4,60})",
        ],
        "hints": [
            "常见形如 xxxx-xxxx-xxxx 的分组串；先查聊天文本，再查小米便签 note.db 的 plain_text（本案便签里就有「google秘钥环」字样）",
            "便签命中后按上下文判断：『秘钥环：xxx』冒号后的串才是答案，别把整句抄上去",
        ],
    },
    "anniversary": {
        "title": "重要日子 / 纪念日",
        "patterns": [r"最重要的日子", r"纪念日", r"生日", r"重要的日子"],
        "kw": ["纪念日", "生日", "最重要的日子", "重要日子", "最重要", "anniversary", "birthday", "在一起", "DaysMatter"],
        "extract": [
            r"(?:纪念日|生日|最重要的日子|anniversary|birthday)[\"']?\s*[=:：是为]+\s*[\"']?([0-9]{4}[-/年.][0-9]{1,2}[-/月.][0-9]{1,2}日?|[0-9]{8})",
            r"((?:19|20)\d{2}[-/年.]\d{1,2}[-/月.]\d{1,2}日?)",
        ],
        # 纪念日类 App 常用 Realm（二进制）存数据，纯文本扫不到：com.clover.daysmatter/files/default.realm
        "files": ["default.realm"],
        "exts": [".realm"],
        "prefer_files": ["*.realm"],
        "validate": r"^(?:19|20)\d{2}[-/年.]\d{1,2}[-/月.]\d{1,2}",
        "hints": [
            "日期可能写成 20200101 / 2020-01-01 / 2020年1月1日；答案行按题面【答案格式】写",
            "聊天上下文里「我们在一起那天/结婚纪念日」通常才是答案，普通生日需甄别",
            "com.clover.daysmatter 的 default.realm 是二进制 Realm 库，本地 sqlite 打不开；用二进制串检索或反序列化取事件日期",
        ],
    },
    "wechat_db_name": {
        "title": "微信聊天记录数据库文件名",
        "patterns": [r"微信.{0,12}数据库", r"聊天记录数据库.{0,6}名称", r"EnMicroMsg"],
        "kw": ["EnMicroMsg", "MicroMsg", "微信"],
        "extract": [r"(EnMicroMsg\.db)", r"(MicroMsg\.db)"],
        "files": ["EnMicroMsg.db", "MicroMsg.db"],
        "hints": [
            "微信库通常是 data/data/com.tencent.mm/MicroMsg/<32位md5>/EnMicroMsg.db；文件名本身常就是答案",
            ".mfs 是加密库，本地 sqlite 打不开，必须用 MCP sqlite_query 且只发 SELECT（PRAGMA 会 not authorized）",
        ],
    },
    "wechat_uin": {
        "title": "微信 UIN",
        "patterns": [r"\buin\b", r"UIN", r"微信账号"],
        "kw": ["default_uin", "uin", "wxid_"],
        "extract": [
            r"default_uin[\"']?\s*[=:]\s*[\"']?([0-9]{5,})",
            r"(?<![A-Za-z])uin[\"']?\s*[=:]\s*[\"']?([0-9]{5,})",
            r"wxid_([A-Za-z0-9]{6,})",
        ],
        # 专指键权重 > 泛键：实测 wxid_ 用户名与杂键里的数字会盖住真 UIN
        "key_weights": [[r"^default_uin$", 3.0], [r"^_auth_uin$", 2.5],
                        [r"^last_login_uin$", 2.5], [r"uin", 1.2]],
        "validate": r"^\d{5,}$",
        "bad": [r"^wxid_", r"^\d{1,4}$"],
        "hints": [
            "UIN 优先看 shared_prefs/system_config_prefs.xml 的 default_uin，或 MicroMsg/<md5> 目录名/account 表",
            "微信库密钥 = md5(IMEI + UIN)（32 位小写）；拿到 UIN 后用 IMEI 拼接校验",
        ],
    },
    "wechat_key": {
        "title": "微信数据库加密密钥",
        "patterns": [r"加密秘钥", r"加密密钥", r"数据库.{0,6}密钥", r"解密.{0,6}密码"],
        "kw": ["enckey", "auth_key", "secret", "密钥"],
        "extract": [
            r"(?:enckey|auth_key|secret)[\"']?\s*[=:]\s*[\"']?([A-Za-z0-9+/=]{16,64})",
            r"(?<![0-9a-fA-F])([0-9a-fA-F]{32})(?![0-9a-fA-F])",
        ],
        "files": ["key_*", "auth_info_key_prefs.xml", "system_config_prefs.xml"],
        "key_weights": [[r"_auth_key$", 2.0], [r"enckey|enc_key", 1.5], [r"key", 1.0]],
        "validate": r"^[0-9a-fA-F]{32}$",
        "pkg_focus": ["com.tencent.mm"],
        "prefer_files": ["auth_info_key_prefs.xml", "system_config_prefs.xml"],
        "exclude_src": ["auth_info_key_prefs.xml"],
        "special": "wechat_key",
        "hints": [
            "库密钥 = md5(IMEI + UIN) 小写 32 位（本检材 IMEI 868139033433456 / UIN 1864810197，脚本已算好）",
            "shared_prefs 里的 _auth_key 是登录 auth key（长 hex），不是 SQLCipher 库密钥，别抄错",
            "不要在 MCP sqlite_query 里发 PRAGMA，列名探测用 sqlite_master / dbq.py --schema",
        ],
    },
    "encrypt_pkg": {
        "title": "文件加密工具包名",
        "patterns": [r"加密(软件|工具|应用)", r"文件加密工具", r"安装.{0,6}加密"],
        "kw": ["aijiami", "jiami", "encrypt", "加固", "加密"],
        "extract": [r"(com\.[A-Za-z0-9_.]{4,})"],
        "hints": [
            "第三方包清单里名字含 aijiami/jiami/encrypt/加固 的就是答案；无用户数据不影响判定",
            "候选来自包名（device_map），不是包内文件内容",
        ],
    },
    "encrypt_algo": {
        "title": "加密方式 / 算法",
        "patterns": [r"加密(方式|算法|模式)", r"AES|MD5|RSA|SM4"],
        "kw": ["EncryptionUtils", "TRANSFORMATION", "AES/", "PKCS7", "Cipher"],
        "extract": [
            r"((?:AES|DES|RSA|SM4|MD5|SHA-\d{1,3})(?:/[A-Za-z0-9/]+)?)",
            r"TRANSFORMATION[=:]\s*[\"']?([^\"';]{4,40})",
        ],
        "hints": [
            "算法串在 dex 里，需要 jadx 反编译 APK 的 EncryptionUtils；grep 命中多为代码片段，别直接当答案",
            "常见答案形如 AES/CBC/PKCS7Padding（见 JADX 中 TRANSFORMATION 常量）",
        ],
    },
    "encrypt_password": {
        "title": "素材加密密码",
        "patterns": [r"素材.{0,8}密码", r"加密密码", r"解密密码"],
        "kw": ["密码", "password", "passphrase"],
        "extract": [
            r"(?:加密密码|解密密码|密码|password|passphrase)[\"']?\s*[=:：是为]+\s*[\"']?([^\"'<>\s，。；}]{3,40})",
        ],
        "hints": [
            "密码常出现在聊天文本里；拿到候选后先跑 aijiami_decrypt.py --probe <file> <password> 用文件头校验",
            "直播素材可能在 pkg/files/Recordings 或 media 下，先确认文件再猜密码",
        ],
    },
    "decrypt_ext": {
        "title": "解密后文件后缀",
        "patterns": [r"解密.{0,6}后缀", r"后缀名", r"扩展名"],
        "kw": ["decrypt", "解密", "extension"],
        "extract": [r"(?:解密后|后缀名|扩展名|extension)[\"']?\s*[=:：是为]+\s*[\"']?([A-Za-z0-9]{2,8})"],
        "hints": ["用 aijiami_decrypt.py 真解一个样本，按真实文件头判断后缀，不要靠猜"],
    },
    "chat_failed": {
        "title": "聊天发送失败条数",
        "patterns": [r"发送失败", r"聊天记录中", r"粉丝"],
        "kw": ["发送失败", "status"],
        "extract": [],
        "hints": [
            "message 表 status=3 为发送失败、2 为正常（本案件实测）",
            "按昵称/uid 过滤 sid 后再数，不要直接 count 全表（Q11 口径 sid=1731375）",
        ],
        "special": "chat_failed",
    },
    "port": {
        "title": "端口号",
        "patterns": [r"端口", r"\bport\b", r"API 服务"],
        "kw": ["端口", "port", "http://", "https://"],
        "extract": [
            r"https?://[^\s\"'<>]+:([0-9]{2,5})",
            r"(?:端口|port)[\"']?\s*[=:：是为]?\s*([0-9]{2,5})",
        ],
        "hints": ["先查聊天文本里的 URL；端口也可能出现在浏览器历史/聊天库"],
    },
    "search_keyword": {
        "title": "搜索关键词",
        "patterns": [r"搜索(过|的)?", r"关键词", r"search"],
        "kw": ["搜索", "search", "history"],
        "extract": [
            r"(?:搜索关键词|搜索词|search(?:ed)?\s*keyword)[\"']?\s*[=:：是为]+\s*[\"']?([^\"'<>\s，。；}]{2,20})",
        ],
        "files": ["dbb_search_tab_key", "dbb_ugc_editor_home_history_biz"],
        "hints": [
            "phonelive 实测：files/mmkv/dbb_ugc_editor_home_history_biz 的 _search_history_info_key；dbb_search_tab_key 只是页签",
        ],
    },
    "clip_count": {
        "title": "剪辑项目数",
        "patterns": [r"剪辑.{0,6}(项目|工程)", r"剪映"],
        "kw": ["newdrafts", "draft"],
        "extract": [],
        "hints": ["com.lemon.lv/files/newdrafts 下 UUID 目录才是工程；files/draft 是占位图不计入"],
        "special": "clip_count",
    },
    "download_url": {
        "title": "下载地址",
        "patterns": [r"下载地址", r"下载链接", r"下载\s*URL"],
        "kw": ["http://", "https://", "下载"],
        "extract": [r"(https?://[^\s\"'<>）)]+)"],
        "hints": [
            "先查聊天文本里的 URL；矿机类 App 的下载地址常只在聊天里被提到",
            "全盘二进制检索也能命中 URL 串，限定 apk/so/db 后缀更省时",
        ],
    },
    "phone_last2": {
        "title": "135 号段手机号末两位",
        "patterns": [r"手机号", r"135", r"末尾两位", r"末两位"],
        "kw": ["web_uid", "135"],
        "extract": [],
        "hints": [
            "短信/通话/联系人 0 行时，查 com.lemon.lv/files/home_feed_cache/key_*.json 的 web_uid（手机号+4位随机）",
            "web_uid 前 11 位才是手机号，后 4 位是随机数；只取前 11 位再取末两位",
        ],
        "special": "phone_uid",
    },
}


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def rel(path: str, root: str) -> str:
    try:
        return os.path.relpath(path, root)
    except Exception:
        return path


def esc(name: str) -> str:
    return str(name).replace('"', '""')


def is_text_col(col: dict) -> bool:
    name = (col.get("name") or "").lower()
    if name in ("id", "_id", "rowid", "_rowid", "docid"):
        return False
    typ = (col.get("type") or "").upper()
    if any(x in typ for x in ("TEXT", "CHAR", "CLOB")):
        return True
    samples = col.get("samples") or []
    return bool(samples) and all(not s.lstrip("-").isdigit() for s in samples)


def text_columns(cols: dict):
    """按价值排序产出文本列：便签 → 聊天库 → 其它，避免几百次 LIKE 把高价值库挤到配额之外。"""
    items = []
    for db, tables in (cols.get("dbs") or {}).items():
        low = db.replace("\\", "/").lower()
        if "com.miui.notes" in low:
            pri = 0
        elif any(k in low for k in ("msg_", "im.db", "message", "chat")):
            pri = 1
        else:
            pri = 2
        for tname, tinfo in tables.items():
            for col in tinfo.get("columns") or []:
                if is_text_col(col):
                    items.append((pri, db, tname, col, int(tinfo.get("rows") or 0)))
    items.sort(key=lambda x: (x[0], x[4]))
    for pri, db, tname, col, rows in items:
        yield db, tname, col, rows


def extract_values(text: str, patterns) -> list:
    out = []
    for p in patterns or []:
        try:
            for m in re.finditer(p, text, re.I):
                v = (m.group(1) if m.groups() else m.group(0)) or ""
                v = v.strip().strip("\"'<>,;，。；：:）)")
                if v:
                    out.append(v)
        except re.error:
            continue
    return out


class Cands:
    def __init__(self):
        self.d = {}

    def add(self, value: str, src: str, weight: float = 1.0):
        value = " ".join(str(value).split()).strip()
        if not value or len(value) > 120:
            return
        entry = self.d.setdefault(value, {"hits": 0.0, "src": []})
        entry["hits"] += weight
        if src not in entry["src"] and len(entry["src"]) < 3:
            entry["src"].append(src)

    def top(self, n: int):
        items = sorted(self.d.items(), key=lambda kv: (-kv[1]["hits"], len(kv[0])))
        return items[:n]


def key_weight(tpl: dict, key: str) -> float:
    """prefs 键名越"专指"权重越高：default_uin 比含 uin 的杂键可信得多。"""
    for pat, w in tpl.get("key_weights") or []:
        try:
            if re.search(pat, key, re.I):
                return float(w)
        except re.error:
            continue
    return 0.7


def score_value(tpl: dict, value: str, weight: float) -> float:
    """按题型校验候选格式：明显不合格式的降权而非丢弃，既压噪声又留线索。"""
    for pat in tpl.get("bad") or []:
        try:
            if re.search(pat, value, re.I):
                return weight * 0.15
        except re.error:
            continue
    ok = tpl.get("validate")
    if ok:
        try:
            if not re.search(ok, value):
                return weight * 0.3
        except re.error:
            pass
    return weight


def addc(cands: "Cands", tpl: dict, value: str, src: str, weight: float = 1.0):
    cands.add(value, src, weight=score_value(tpl, value, weight))


def like_search(db_path: str, table: str, column: str, kws, cap: int = 2) -> list:
    uri = "file:///" + db_path.replace("\\", "/") + "?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=3)
    except Exception:
        return []
    out = []
    try:
        for kw in kws:
            if len(out) >= cap:
                break
            try:
                rows = con.execute(
                    'select cast("%s" as text) from "%s" where cast("%s" as text) like ? limit %d'
                    % (esc(column), esc(table), esc(column), cap), ("%" + kw + "%",)).fetchall()
            except Exception:
                continue
            for (v,) in rows:
                v = " ".join(str(v).split())
                if v:
                    out.append(v)
    finally:
        try:
            con.close()
        except Exception:
            pass
    return out


def run_db_search(tpl: dict, cols: dict, cands: Cands, root: str, deadline: float) -> int:
    kws = tpl.get("kw") or []
    if not kws:
        return 0
    focus = tpl.get("pkg_focus") or []
    queries = 0
    for db, tname, col, rows in text_columns(cols):
        if focus and not any(f in db for f in focus):
            continue  # 语料范围外的库不查，避免噪声（如微信题去查 laz.note 的 32 位串）
        if time.time() > deadline or queries >= MAX_QUERIES:
            break
        cname = col.get("name") or ""
        sample_hit = any(
            any(str(k).lower() in str(s).lower() for s in (col.get("samples") or []))
            for k in kws)
        if not sample_hit and rows > 2000:
            continue
        hits = like_search(db, tname, cname, kws, cap=2)
        queries += 1
        for h in hits:
            vals = extract_values(h, tpl.get("extract") or [])
            if vals:
                for v in vals[:2]:
                    addc(cands, tpl, v, "%s | %s.%s" % (rel(db, root), tname, cname), 1.2)
            elif len(h) <= 60:
                addc(cands, tpl, h, "%s | %s.%s(raw)" % (rel(db, root), tname, cname), 0.3)
    return queries


def iter_pkg_files(map_data: dict, root: str, deadline: float, tpl: dict = None):
    """只扫已在地图里的目录（shared_prefs / files 一级子目录），不整盘 walk。

    模板可加 "exts" 扩展名（如 .realm）与 "files" 精确文件名，用来抓非文本库。
    """
    layout = map_data.get("layout") or "classic"
    data_data = Path(root) / "data" / "data" if layout == "classic" else Path(root) / "data"
    exts = (".xml", ".json", ".txt", ".prop", ".cfg", ".ini", ".properties")
    exts = exts + tuple((tpl or {}).get("exts") or [])
    names = set((tpl or {}).get("files") or [])
    for pkg in map_data.get("packages") or []:
        if time.time() > deadline:
            return
        pkg_dir = data_data / pkg.get("pkg", "")
        dirs = [pkg_dir / "shared_prefs"]
        for d in (pkg.get("top_dirs") or [])[:8] + (pkg.get("files_dirs") or [])[:12]:
            name = d.get("name")
            if name:
                dirs.append(pkg_dir / name)
                dirs.append(pkg_dir / "files" / name)
        # files 根目录下的散文件（Realm / 单文件库就放这里）
        dirs.append(pkg_dir / "files")
        for d in dirs:
            if not d.is_dir():
                continue
            try:
                entries = sorted(os.scandir(d), key=lambda e: e.name)[:80]
            except OSError:
                continue
            for e in entries:
                try:
                    if not e.is_file():
                        continue
                    if not (e.name.lower().endswith(exts) or e.name in names):
                        continue
                    if e.stat().st_size > MAX_FILE_BYTES:
                        continue
                except OSError:
                    continue
                yield Path(e.path)


def find_named(base: Path, pattern: str, depth: int = 4, cap: int = 12):
    """在指定目录下按名字找文件（限制深度与访问目录数）。"""
    rx = re.compile(pattern)
    hits = []
    base_depth = len(base.parts)
    visited = 0
    try:
        for cur, dirs, files in os.walk(base):
            visited += 1
            if visited > 1500 or len(hits) >= cap:
                break
            if len(Path(cur).parts) - base_depth >= depth:
                dirs[:] = []
            for f in files:
                if rx.search(f):
                    hits.append(Path(cur) / f)
                    if len(hits) >= cap:
                        break
            if len(hits) >= cap:
                break
    except OSError:
        pass
    return hits


def run_file_search(tpl: dict, map_data: dict, root: str, cands: Cands, deadline: float, entries: list):
    kws = [k for k in (tpl.get("kw") or []) if k]
    name_pats = tpl.get("files") or []
    props = tpl.get("props") or []
    focus = tpl.get("pkg_focus") or []
    prefer = tpl.get("prefer_files") or []
    scanned = 0
    paths = list(iter_pkg_files(map_data, root, deadline, tpl))
    paths += list(iter_root_files(tpl, root, map_data, deadline))
    for path in paths:
        if time.time() > deadline or scanned >= 800:
            break
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:300000]
        except Exception:
            continue
        src = rel(str(path), root)
        low_src = src.replace("\\", "/").lower()
        if any(n in low_src for n in SDK_NOISE):
            continue
        if any(n in low_src for n in (tpl.get("exclude_src") or [])):
            continue
        named = any(fnmatch_name(path.name, p) for p in name_pats)
        before = len(cands.d)
        hit = False

        # 包范围/偏好文件加权：wechat_key 只信 com.tencent.mm；纪念日只信 realm
        boost = 1.0
        if focus:
            boost = 2.0 if any(f in src for f in focus) else 0.4
        if prefer and any(fnmatch_name(path.name, p) for p in prefer):
            boost *= 3.0

        # SharedPreferences / XML：按键名匹配后直接取 value，比在整段文本上套正则可靠
        for key, value in parse_prefs(text):
            if any(k.lower() in key.lower() for k in kws):
                hit = True
                if value:
                    w = key_weight(tpl, key) * boost
                    addc(cands, tpl, value[:120], "%s | %s" % (src, key), w)
                    if len(value) > 120:
                        addc(cands, tpl, value[:32], "%s | %s（仅前32字符）" % (src, key), w * 0.4)
                    if w >= 2.0 and src in entries:
                        entries.remove(src)  # 专指键命中，入口提到最前
                    if w >= 2.0 and src not in entries and len(entries) < 10:
                        entries.insert(0, src)

        # persistent_properties 这类 protobuf 键值
        for key in props:
            v = props_value(text, key)
            if v:
                hit = True
                addc(cands, tpl, v[:120], "%s | %s" % (src, key), 1.5 * boost)

        # 模板正则
        for v in extract_values(text, tpl.get("extract") or [])[:3]:
            hit = True
            addc(cands, tpl, v, src, boost)

        # 命中但没有抓到结构化值：把含关键词的行降权放进来当线索
        if hit and len(cands.d) == before:
            for line in text.splitlines():
                low = line.lower()
                if any(k.lower() in low for k in kws) and len(line.strip()) <= 100:
                    addc(cands, tpl, line.strip(), src + "（原文行）", 0.3 * boost)
                    break

        if named and not hit and len(path.name) <= 80:
            addc(cands, tpl, path.name, src, 0.8 * boost)
        # Realm/二进制库里命中的事件标题写进入口：日期是同一记录的另一字段，靠标题定位比猜日期可靠
        if path.suffix.lower() == ".realm" and hit:
            found = []
            for kw in kws:
                if not kw or kw not in text:
                    continue
                for m in re.finditer(r"[\u4e00-\u9fa5A-Za-z0-9 ]{0,12}" + re.escape(kw) + r"[\u4e00-\u9fa50-9 ]{0,8}", text):
                    found.append(m.group(0).strip())
            if found:
                best_title = max(found, key=len)  # 越长越具体：「我一生中最重要日子」胜过「生日」
                entries.append("%s（命中标题「%s」，日期在同一条记录）" % (src, best_title))
        if (hit or named) and src not in entries and len(entries) < 10:
            entries.append(src)
    return scanned


def fnmatch_name(name: str, pat: str) -> bool:
    if "*" in pat or "?" in pat:
        import fnmatch
        return fnmatch.fnmatch(name, pat)
    return name == pat


def parse_prefs(text: str) -> list:
    """Android SharedPreferences / XML 配置里的 name=value 对。"""
    pairs = []
    for m in re.finditer(r'name="([^"]+)"[^>]*value="([^"]*)"', text):
        pairs.append((m.group(1), m.group(2)))
    for m in re.finditer(r'<string name="([^"]+)">([^<]*)</string>', text):
        pairs.append((m.group(1), m.group(2)))
    return pairs


def props_value(text: str, key: str):
    """persistent_properties 是 protobuf：key 后跟控制字节，再跟值。"""
    i = text.find(key)
    if i < 0:
        return None
    j = i + len(key)
    while j < len(text) and ord(text[j]) < 32:
        j += 1
    out = []
    while j < len(text) and ord(text[j]) >= 32:
        out.append(text[j])
        j += 1
    v = "".join(out).strip()
    return v or None


def iter_root_files(tpl: dict, root: str, map_data: dict, deadline: float):
    base = Path(root)
    for pat in tpl.get("root_files") or []:
        target = base / pat
        if any(ch in pat for ch in "*?"):
            for p in sorted(base.glob(pat)):
                if p.is_file():
                    yield p
        elif target.is_file():
            yield target
    # 媒体根目录：App 外的散落库/文本（EnMicroMsg.db 就在这类位置）
    layout = map_data.get("layout") or "classic"
    media = base / "data" / "media" / "0" if layout == "classic" else base / "media" / "0"
    if media.is_dir():
        names = tpl.get("files") or []
        kws = [k for k in (tpl.get("kw") or []) if len(k) >= 3]
        try:
            entries = sorted(os.scandir(media), key=lambda e: e.name)[:30]
        except OSError:
            entries = []
        for e in entries:
            if time.time() > deadline:
                return
            try:
                if not e.is_file() or e.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            if any(fnmatch_name(e.name, n) for n in names) or any(k.lower() in e.name.lower() for k in kws):
                yield Path(e.path)


def add_note_entry(root: str, map_data: dict, entries: list):
    """小米便签 note.db 是密码/暗号/秘钥环的高频落点（本案件实测 Q2/Q4 线索在此）。"""
    layout = map_data.get("layout") or "classic"
    data_data = Path(root) / "data" / "data" if layout == "classic" else Path(root) / "data"
    p = data_data / "com.miui.notes" / "databases" / "note.db"
    if p.is_file():
        entries.append(rel(str(p), root) + "（便签库：note.plain_text/snippet 常藏密码/暗号/秘钥环）")


def special_handlers(name: str, tpl: dict, map_data: dict, root: str, cands: Cands, entries: list, deadline: float):
    layout = map_data.get("layout") or "classic"
    data_data = Path(root) / "data" / "data" if layout == "classic" else Path(root) / "data"

    if name == "wechat_key":
        # 微信库密钥 = md5(IMEI + UIN)；_auth_key 只是登录 auth key，长 hex 不是答案
        mm = data_data / "com.tencent.mm" / "shared_prefs"
        uin = None
        for fn in ("auth_info_key_prefs.xml", "system_config_prefs.xml", "com.tencent.mm_preferences.xml"):
            p = mm / fn
            if not p.is_file():
                continue
            try:
                t = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            entries.append(rel(str(p), root))
            if not uin:
                m = re.search(r'name="(?:default_uin|_auth_uin|last_login_uin)"[^>]*value="([0-9]{5,})"', t) \
                    or re.search(r'name="(?:default_uin|_auth_uin)"[^>]*value="([0-9]{5,})"', t)
                if m:
                    uin = m.group(1)
        imei = None
        for rel_path in ("com.android.browser/shared_prefs/_m_rec.xml",
                         "com.android.mms/shared_prefs/mi_stat_pref.xml",
                         "com.android.browser/shared_prefs/mi_stat_pref.xml"):
            p = data_data / rel_path
            if not p.is_file():
                continue
            try:
                t = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            m = re.search(r'name="imei\d?"[^>]*>([0-9]{15})<', t) \
                or re.search(r'"imei\d?"\s*[=:>]\s*"([0-9]{15})', t)
            if m:
                imei = m.group(1)
                entries.append(rel(str(p), root))
                break
        if imei and uin:
            addc(cands, tpl, hashlib.md5((imei + uin).encode()).hexdigest(),
                 "md5(IMEI+UIN)=md5(%s+%s)（标准公式，首选）" % (imei, uin), 6.0)
            addc(cands, tpl, hashlib.md5((uin + imei).encode()).hexdigest(),
                 "md5(UIN+IMEI) 备选", 0.8)
        elif uin:
            cands.add("UIN=%s，缺 IMEI" % uin, "prefs（需补 IMEI 才能算 md5）", weight=0.2)
        md5_file = data_data / "com.tencent.mm" / "files" / "host" / "getdns.ini"
        if md5_file.is_file():
            entries.append(rel(str(md5_file), root))
        return
    if name == "phone_uid":
        for pkg in map_data.get("packages") or []:
            if pkg.get("pkg") != "com.lemon.lv":
                continue
            feed = data_data / "com.lemon.lv" / "files" / "home_feed_cache"
            if not feed.is_dir():
                break
            entries.append(rel(str(feed), root))
            try:
                files = [e for e in os.scandir(feed) if e.is_file() and e.name.endswith(".json")][:40]
            except OSError:
                files = []
            for f in files:
                if time.time() > deadline:
                    break
                try:
                    text = Path(f.path).read_text(encoding="utf-8", errors="replace")[:200000]
                except Exception:
                    continue
                for m in re.finditer(r'"web_uid"\s*:\s*"([0-9]{11,16})"', text):
                    uid = m.group(1)
                    src = rel(f.path, root)
                    entries.append(src)
                    cands.add(uid[:11], "%s（完整 web_uid=%s）" % (src, uid), weight=0.6)
                    if len(uid) >= 13 and uid.startswith("135"):
                        cands.add(uid[9:11], "%s（135 号段末两位）" % src)
        return

    if name == "clip_count":
        for pkg in map_data.get("packages") or []:
            if pkg.get("pkg") != "com.lemon.lv":
                continue
            drafts = data_data / "com.lemon.lv" / "files" / "newdrafts"
            if not drafts.is_dir():
                break
            entries.append(rel(str(drafts), root))
            uuids = []
            try:
                for e in os.scandir(drafts):
                    if e.is_dir() and re.fullmatch(r"[0-9a-fA-F-]{16,}", e.name):
                        uuids.append(e.name)
            except OSError:
                pass
            cands.add(str(len(uuids)), "%s（UUID 目录 %d 个）" % (rel(str(drafts), root), len(uuids)))
            if uuids:
                entries.append("UUID 示例: " + ", ".join(uuids[:5]))
        return

    if name == "chat_failed":
        for pkg in map_data.get("packages") or []:
            for chat in pkg.get("chat_dbs") or []:
                for fname in chat.get("files") or []:
                    db = Path(chat.get("dir", "")) / fname
                    if not db.is_file() or time.time() > deadline:
                        continue
                    entries.append(rel(str(db), root))
                    try:
                        con = sqlite3.connect(
                            "file:///" + str(db).replace("\\", "/") + "?mode=ro", uri=True, timeout=3)
                    except Exception:
                        continue
                    try:
                        total = con.execute(
                            'select count(*) from message where status=3').fetchone()[0]
                        cands.add(str(total), "%s | message.status=3 全表" % rel(str(db), root))
                        cols = [r[1] for r in con.execute('PRAGMA table_info(message)').fetchall()]
                        if "sid" in cols:
                            rows = con.execute(
                                'select sid, count(*) from message where status=3 '
                                'group by sid order by 2 desc limit 5').fetchall()
                            for sid, n in rows:
                                cands.add(str(n), "%s | sid=%s status=3" % (rel(str(db), root), sid), weight=0.6)
                    except Exception:
                        pass
                    finally:
                        try:
                            con.close()
                        except Exception:
                            pass
        return


# 题面同时命中多个模板时，按这些强规则先定题型（Q8 既有"数据库"又有"加密秘钥"）
PRIORITY_RULES = [
    (r"秘钥环|密钥环", "keyring"),
    (r"加密(秘钥|密钥)|数据库.{0,12}(秘钥|密钥)", "wechat_key"),
    (r"数据库.{0,8}(名称|文件名|名字)|数据库文件", "wechat_db_name"),
]


def guess_type(text: str):
    if not text:
        return None
    for pat, name in PRIORITY_RULES:
        if re.search(pat, text, re.I):
            return name
    best, score = None, 0
    for name, tpl in TEMPLATES.items():
        s = sum(1 for p in tpl.get("patterns") or [] if re.search(p, text, re.I))
        if s > score:
            best, score = name, s
    return best


def fallback_entries(root: str, map_data: dict) -> list:
    """本层全空时也要留下"该去哪找"的关键线索，别让模型从 0 开始瞎逛。"""
    out = []
    if MAP_JSON.is_file():
        out.append(str(MAP_JSON) + "（表格化数据源，用脚本过滤，不要整份读）")
    if MAP_JSON.with_suffix(".summary.txt").is_file() or (NOTES_DIR / "device_map.summary.txt").is_file():
        out.append(str(NOTES_DIR / "device_map.summary.txt") + "（一屏摘要：包清单/明文库/媒体根）")
    layout = map_data.get("layout") or "classic"
    media = Path(root) / "data" / "media" / "0" if layout == "classic" else Path(root) / "media" / "0"
    if media.is_dir():
        out.append(str(media) + "（媒体根目录：常放散落的加密库/导出文件）")
    if root:
        data_data = Path(root) / "data" / "data" if layout == "classic" else Path(root) / "data"
        out.append(str(data_data) + "（App 私有目录根）")
    return out


def keywords_from_text(text: str) -> list:
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_.-]{2,}|[\u4e00-\u9fa5]{2,8}", text or "")
    out = []
    for w in words:
        if any(s in w for s in STOPWORDS) and len(w) <= 6:
            continue
        w = w.strip("的了吗呢")
        if len(w) >= 2 and w not in out:
            out.append(w)
    return out[:8]


def render(kind: str, tpl: dict, cands: Cands, entries: list, extra_hints: list, limit: int) -> str:
    lines = ["# evidence pack · %s" % kind]
    if tpl.get("title"):
        lines.append("题型：%s" % tpl["title"])
    lines.append("")
    lines.append("## 候选值（按证据数排序；必须自己复核后再写答案，禁止直接照抄）")
    top = cands.top(limit)
    if not top:
        lines.append("- （本层未命中：按下面入口再走 B/C 级，或写 UNKNOWN + 线索）")
    for i, (value, meta) in enumerate(top, 1):
        lines.append("%d. %s  ×%s  ← %s" % (i, value, round(meta["hits"], 1), "；".join(meta["src"][:2])))
    lines.append("")
    lines.append("## 取数入口")
    seen = []
    for e in entries:
        if e and e not in seen:
            seen.append(e)
    for e in seen[:10]:
        lines.append("- %s" % e)
    if not seen:
        lines.append("- （无：先跑 myos_mount.py mount + myos_appmap.py，按 summary 的包清单定位）")
    hints = [h for h in (tpl.get("hints") or []) + extra_hints if h]
    if hints:
        lines.append("")
        lines.append("## 提示")
        for h in hints:
            lines.append("- %s" % h)
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", type=int, default=0, help="题号：生成 notes/evidence-q<N>.txt")
    ap.add_argument("--text", default="", help="题面；不给则从 questions-*.txt 取")
    ap.add_argument("--type", default="", help="强制题型；见 --list")
    ap.add_argument("--limit", type=int, default=6, help="候选值上限")
    ap.add_argument("--list", action="store_true", help="列出支持的题型")
    ap.add_argument("--out", default="", help="输出路径；默认 notes/evidence-q<N>.txt")
    args = ap.parse_args()

    if args.list:
        for name, tpl in TEMPLATES.items():
            print("%-16s %s" % (name, tpl.get("title", "")))
        return 0

    text = args.text
    if not text and args.q:
        for qf in sorted(NOTES_DIR.glob("questions-*.txt")):
            try:
                for line in qf.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.strip().startswith("%d|" % args.q):
                        text = line.split("|", 1)[1].strip()
                        break
            except Exception:
                continue
            if text:
                break

    kind = args.type or guess_type(text) or "generic"
    tpl = TEMPLATES.get(kind, {})
    if not tpl:
        tpl = {"title": "通用检索（未识别题型）", "kw": keywords_from_text(text),
               "extract": [], "hints": ["未识别题型：按题面关键词做 LIKE 检索，命中后需人工确认语义"]}
        kind = "generic"

    deadline = time.time() + DEADLINE_SECONDS
    map_data = load_json(MAP_JSON)
    cols = load_json(COLS_JSON)
    root = str(map_data.get("root") or cols.get("root") or "")
    cands, entries, extra_hints = Cands(), [], []

    if tpl.get("special"):
        special_handlers(tpl["special"], tpl, map_data, root, cands, entries, deadline)
    if root:
        add_note_entry(root, map_data, entries)
    queries = run_db_search(tpl, cols, cands, root, deadline)
    files = 0
    if root and Path(root).is_dir():
        files = run_file_search(tpl, map_data, root, cands, deadline, entries)
    elif not root:
        extra_hints.append("device_map.json 缺少 root：先跑 myos_appmap.py，或检查挂载")
    if not entries:
        entries = fallback_entries(root, map_data)
        extra_hints.append("本层未命中：答案可能在加密库/Realm/聊天文本里，按下面入口定向打开，不要重新枚举包")

    extra_hints.append("数据源：明文库 %d 个，列名地图 %d 列，本次 LIKE 查询 %d 次，扫描文件 %d 个"
                       % (cols.get("dbs") and len(cols["dbs"]) or 0,
                          sum(len(t["columns"]) for tables in (cols.get("dbs") or {}).values()
                              for t in tables.values()),
                          queries, files))

    body = render(kind, tpl, cands, entries, extra_hints, args.limit)
    out = Path(args.out) if args.out else (NOTES_DIR / ("evidence-q%d.txt" % args.q) if args.q else None)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
        body = body + "\n（已写入 %s）\n" % out
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
