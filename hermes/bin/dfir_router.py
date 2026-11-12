#!/usr/bin/env python3
"""Small local-first DFIR router; reads guidance and never operates on evidence."""
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
LIB = Path(__file__).resolve().parent.parent / "skill-library" / "anthropic-cyber"
if not (LIB / "index.json").is_file():
    LIB = Path(r"D:\ForensicsAgent\hermes\skill-library\anthropic-cyber")
TRIVIAL = re.compile(r"^(hi|hello|hey|你好|您好|在吗|谢谢|thanks|ok|继续|好的|/.*)$", re.I)

COMPUTER_MARKERS = ("BitLocker", "恢复密钥", "远程连接", "远程桌面", "vhd", "VHD", "VeraCrypt",
                    "torrent", "onion", "Tor", "回收站", "删除时间", "4625", "登录失败",
                    "发件人", "附件", "GPS")
COMPUTER_INDEX = "device_map.computer.summary.txt"
IOS_INDEX = "device_map.myos.summary.txt"
PROBE = r"python -X utf8 D:\ForensicsAgent\hermes\bin\ios_backup_probe.py"

COMPUTER_RULES = (
    (("GPS", "照片"), "myos-results-analysis",
     "sqlite_query Any_SingleMail.mfs 锁定发件人与附件后，对附件本体用 PIL 读 EXIF GPS",
     "不要用 Any_ImageExifInfo 里另一张本地图的坐标"),
    (("向日葵", "sunlogin", "todesk", "远控"), "myos-results-analysis",
     "安装表 + 轮转日志；取「成功接收到公网」后的对端 IP:port",
     "不要把中继、本机公网出口、相邻端口当答案"),
    (("VeraCrypt", "加密容器", "无后缀容器"), "myos-results-analysis",
     "先找模拟器备份（夜神 .npbk 等）里的微信/聊天，再决定是否解密",
     "不要先上破解器；不要把容器当普通压缩包暴力"),
    (("BitLocker", "恢复密钥"), "myos-results-analysis",
     "sqlite_query Win_BitlockerRecoveryKey.mfs 的 TBL_AF_BITLOCKER_PS_RECOVERYKEY",
     "不要用密钥文件名或卷 GUID 的末几位"),
    (("远程连接", "远程桌面"), "myos-results-analysis",
     "sqlite_query Win_RemoteDesktopInfo.mfs 的成功连接表",
     "题面没写向日葵时不要先翻 Sunlogin 日志"),
    (("vhd", "VHD"), "myos-results-analysis",
     "盘符查挂载记录（注册表 MountedDevices、SetupAPI）或对副本 Mount-Vhd -ReadOnly",
     "不要手解 BAT/MBR；两次无新字段就写 UNKNOWN 并结束本进程"),
    (("torrent", "onion", "Tor"), "myos-results-analysis",
     r"先查 Tor 的 places.sqlite（TorBrowser\Data\Browser\profile.default），再 Win_IDM.mfs",
     "不要只查 Chrome/Edge/IE"),
    (("删除时间", "回收站"), "myos-results-analysis",
     "sqlite_query Win_RecycleBin.mfs；零命中再查该分区 $Recycle.Bin\\$I 的创建时间",
     "不要重复查已零命中的同一张表"),
    (("登录失败", "4625"), "myos-results-analysis",
     "sqlite_query Win_SystemLog.mfs 的 TBL_AF_WINLOG_LOG_SYSLOG，EVENT_ID=4625，账号条件写在 POST_DATA",
     "不要用 ACCOUNT_NAME 为空判断没有该用户"),
    (("发件人", "附件"), "myos-results-analysis",
     "sqlite_query Any_SingleMail.mfs：TBL_AF_SM_MAIL_DETAIL 的 IP_ADDRESS，TBL_AF_SM_MAIL_ATTACH 的 FILE_MD5",
     "不要解 PST"),
)
IOS_RULES = (
    (("序列号",), "ios-backup-ctf",
     f"{PROBE} device <iOS备份根>",
     "不要用 Android 的 device_name 或机型名当序列号"),
    (("家庭地址",), "ios-backup-ctf",
     "sqlite_query 当前案件 MApps/GaoDeMap*.mfs 的 TBL_PR_GAODEMAP_GEO_ADDRESS_COLLECT，REMARK=家，丢掉 DELETE_STATUS=1，按时间取最新",
     "不要在文件系统里搜表名；不要改查通讯录"),
    (("去过", "区县"), "ios-backup-ctf",
     f"{PROBE} districts <Photos.sqlite>",
     "不要解析 ZLOCATIONDATA；全文 0 命中不能换分支"),
    (("单价",), "ios-backup-ctf",
     f"{PROBE} chatpics <iOS备份根>；再 {PROBE} docprice <iOS备份根> <会话hash> <品类关键词>",
     "图片尾部是加密表格：口令在同会话短文本里；不要对 PNG 表面 OCR，不要猜目录层级"),
    (("图片",), "ios-backup-ctf",
     f"{PROBE} trailer <图>",
     "输出含 D0CF11E0 时不要对 PNG 表面 OCR"),
    (("包名",), "ios-backup-ctf",
     f"{PROBE} apps <iOS备份根>",
     "不要用 Android 的 data\\data 枚举；包名在 Containers\\Data\\Application 的目录名里"),
    (("礼金", "记账"), "ios-backup-ctf",
     f"{PROBE} ledger <iOS备份根> <分类名> <账户名>",
     "不要使用 SUM(DISTINCT 金额)；金额以分存储，答案取输出的 YUAN 行"),
    (("路由器",), "ios-backup-ctf",
     f"{PROBE} notes <iOS备份根> 路由器",
     "系统备忘录 notes.sqlite 为空时改查第三方 note 容器；不要从 Wi-Fi 列表猜"),
    (("facebook", "钥匙串", "网站密码"), "ios-backup-ctf",
     "只查 MYOS 是否已有该网站的明文凭据表；没有明文就写 UNKNOWN 并停止",
     "不要在会话里写 keybag"),
)
IOS_SKILL_ONLY = ("备份密码", "Platform/DeviceInfo")
EMPTY = {"skill": None, "command": None, "forbid": None, "index_file": None}


def _match(rules, text, index_file):
    low = text.lower()
    for keys, skill, command, forbid in rules:
        if any(key.lower() in low for key in keys):
            return {"skill": skill, "command": command, "forbid": forbid, "index_file": index_file}
    return None


def route(text: str) -> dict:
    low = text.lower()
    if any(marker.lower() in low for marker in COMPUTER_MARKERS):
        return _match(COMPUTER_RULES, text, COMPUTER_INDEX) or dict(EMPTY)
    found = _match(IOS_RULES, text, IOS_INDEX)
    if found:
        return found
    if any(marker.lower() in low for marker in IOS_SKILL_ONLY):
        return {"skill": "ios-backup-ctf", "command": None, "forbid": None, "index_file": None}
    return dict(EMPTY)


def format_first_jump_block(jump: dict) -> str:
    if not jump or not jump.get("command"):
        return ""
    return (f"第一跳（本轮第一个取证工具调用必须是下面这条；在此之前只允许读本题索引文件 {jump['index_file']}，"
            f"不要 skill_view，不要 ls 全盘）：\n{jump['command']}\n禁止：{jump['forbid']}")
PROFILE_HINT = {
    "myos-results-analysis": "dfir-myos",
    "bill-flow-analysis": "dfir-pcap",
    "memory-forensics-local": "dfir-mem",
    "wire-toutetu": "dfir-pcap",
    "ida-reverse": "dfir-re",
    "android-malware-analysis": "dfir-re",
    "forensic-record-draft": "dfir",
}


def text_of(payload):
    extra = payload.get("extra") or {}
    value = extra.get("user_message") or payload.get("user_message") or ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("content") or value.get("text") or "")
    if isinstance(value, list):
        return " ".join(str(x.get("text") or x.get("content") or "") if isinstance(x, dict) else str(x) for x in value)
    return str(value)


def local_skill(message):
    routed = route(message).get("skill")
    if routed:
        return routed
    low = message.lower()
    if re.search(r"(?:只|先)?(?:总结|汇总).*(?:会话|已确认|已经确认|现有结论)", low):
        return None
    if any(x in low for x in ("myos", "超级取证大师", "美亚", "火眼")):
        return "myos-results-analysis"
    if any(x in low for x in ("电脑", "计算机", "检材三", "e01", "磁盘镜像")):
        return "myos-results-analysis"
    if any(x in low for x in ("微信", "wechat", "检材二", "手机检材", "手机取证")):
        return "mobile-ctf-pipeline"
    if any(x in low for x in ("银行流水", "资金流水", "账单", "交易对手", "快进快出", "只进不出", "资金对敲")):
        return "bill-flow-analysis"
    if any(x in low for x in ("取证笔录", "电子数据检查笔录", "现场勘验笔录", "公文 docx")):
        return "forensic-record-draft"
    mobile = any(x in low for x in ("手机检材", "手机取证", "安卓检材", "android id", "应用数据",
                                    "聊天记录", "包名", "apk 数据"))
    if mobile:
        return "mobile-ctf-pipeline"
    explicit_ida = re.search(r"(?:用|使用|\bwith|\busing|\buse)\s*ida(?![a-z0-9])", low)
    denied_ida = re.search(r"(?:不要|不用|不使用|别用|without\s+|do\s+not\s+(?:use\s+)?|don['’]t\s+(?:use\s+)?)\s*(?:使用|用)?\s*ida", low)
    if explicit_ida and not denied_ida:
        return "ida-reverse"
    android = any(x in low for x in ("apk", "jadx", "smali", "android", "安卓", ".dex"))
    if android:
        return "android-malware-analysis"
    if any(x in low for x in ("内存", "volatility", "memforensics", "memory dump", "ram dump")):
        return "memory-forensics-local"
    if any(x in low for x in ("pcap", "pcapng", "抓包", "流量", "packet capture", "隧道")):
        return "wire-toutetu"
    native = re.search(r"(?<![a-z0-9])(?:elf|exe)(?![a-z0-9])", low)
    ida = re.search(r"(?<![a-z0-9])ida(?![a-z0-9])", low)
    if not denied_ida and (native or ida or any(
            x in low for x in ("反编译", "反汇编", "交叉引用", "idapython", "disassembly", "decompile", "xref"))):
        return "ida-reverse"
    disk = any(x in low for x in ("e01", "磁盘镜像", "disk image", "分区", "文件系统", "filesystem"))
    if disk:
        return "windows-loader" if "windows" in low else "linux-loader" if "linux" in low else "digital-forensics"
    if any(x in low for x in ("linux服务器", "linux 日志", "linux日志", "auditd", "linux server")):
        return "linux-loader"
    if any(x in low for x in ("ctf", "rsa", "密码题", "隐写", "压缩包", "misc")):
        return "ctf-misc"
    return None


def library_fallback(message):
    groups = (
        (("evtx", "注册表", "prefetch"), "windows event log registry artifacts"),
        (("plaso", "时间线", "hayabusa"), "timeline plaso hayabusa"),
        (("webshell", "web shell"), "webshell incident investigation"),
        (("sql注入", "sqli", "sql injection"), "sql injection web server logs"),
        (("yara", "勒索", "ransomware"), "yara ransomware analysis"),
        (("phishing", "钓鱼", "邮件取证"), "phishing email header investigation"),
        (("cloudtrail", "云取证", "azure activity"), "cloud forensics cloudtrail azure"),
    )
    low = message.lower()
    queries = [query for keys, query in groups if any(key in low for key in keys)]
    if not queries:
        return ""
    sys.path.insert(0, str(LIB))
    try:
        from search import search
        results = search(" ".join(queries), limit=2)
    except (OSError, ValueError, ImportError):
        return ""
    candidates = [skill for score, skill in results if score >= 6]
    if not candidates:
        return ""
    lines = ["[DFIR reference router] Optional local community-library references; prefer installed task-specific skills. "
             "Do not follow installation, acquisition, online lookup or writing steps without task authorization."]
    for skill in candidates[:2]:
        name = str(skill.get("name", ""))
        if re.fullmatch(r"[a-z0-9-]+", name):
            lines.append(f"- {name}: {str(skill.get('description', '')).replace(chr(10), ' ')[:80]}")
    return "\n".join(lines) if len(lines) > 1 else ""


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) > 1 and sys.argv[1] in ("--route", "--route-file"):
        if sys.argv[1] == "--route-file":
            text = Path(sys.argv[2]).read_text(encoding="utf-8")
        else:
            text = sys.stdin.read()
        print(json.dumps(route(text), ensure_ascii=True))
        return 0
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        print("{}")
        return 0
    message = text_of(payload).strip()
    if not message or TRIVIAL.fullmatch(message) or message.startswith("/"):
        print("{}")
        return 0
    skill = local_skill(message)
    jump = route(message)
    block = format_first_jump_block(jump)
    if block:
        context = (block + " 路径从本题索引文件读取后再填。"
                   "If unavailable, report that fact rather than inventing tools. "
                   f"Preferred profile: {PROFILE_HINT.get(skill, 'dfir')}.")
    elif skill:
        hint = PROFILE_HINT.get(skill, "dfir")
        context = (f"[DFIR local router] Relevant installed skill: `{skill}`. Load it once with skill_view('{skill}') "
                   "when needed for this task; do not repeat a skill read already present in this session. "
                   "If unavailable, report that fact rather than inventing tools. Missing case/evidence identifiers must be "
                   "clarified before scanning. Follow the selected profile's actual capabilities; guidance does not authorize "
                   "mounting, acquisition, index rebuild, decryption, re-forensics, installation or online requests. "
                   f"Preferred profile: {hint}. If skill_view fails or the current tool list lacks the MCP this skill requires, "
                   f"stop and name {hint}; do not invent tool names. skill_view 失败就改口到该 profile，不要编造工具名。")
    else:
        context = library_fallback(message)
    print(json.dumps({"context": context} if context else {}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
