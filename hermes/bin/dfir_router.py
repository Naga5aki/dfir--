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
    if skill:
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
