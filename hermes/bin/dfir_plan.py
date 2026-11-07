#!/usr/bin/env python3
"""Case-agnostic DFIR question router and plan builder.

This module deliberately contains no case/answer/table names. It classifies a
question by domain + task, then chooses a profile, skills and a bounded budget.
A case can override any decision with notes/case-profile.json or the legacy
complex-questions.txt / deep-questions.txt sidecars.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_BUDGETS = {
    "base": {"turns": 12, "seconds": 480},
    "complex": {"turns": 16, "seconds": 600},
    "deep": {"turns": 18, "seconds": 660},
    "retry": {"turns": 6, "seconds": 240},
}
DEFAULT_PROFILES = {
    "mobile": {"base": "dfir-myos", "deep": "dfir-max"},
    "computer": {"base": "dfir-myos", "deep": "dfir-max"},
    "pc": {"base": "dfir", "deep": "dfir-max"},
    "network": {"base": "dfir-pcap", "deep": "dfir-pcap"},
    "memory": {"base": "dfir-mem", "deep": "dfir-mem"},
    "reverse": {"base": "dfir-re", "deep": "dfir-re", "mobile": "dfir-max"},
    "bill": {"base": "dfir-pcap", "deep": "dfir-pcap"},
    "linux": {"base": "dfir", "deep": "dfir-max"},
    "mac": {"base": "dfir", "deep": "dfir-max"},
    "cloud": {"base": "dfir", "deep": "dfir-max"},
    "email": {"base": "dfir", "deep": "dfir-max"},
    "database": {"base": "dfir", "deep": "dfir-max"},
    "generic": {"base": "dfir", "deep": "dfir-max"},
}
DEFAULT_SKILLS = {
    "mobile": ["android-app-forensics", "mobile-ctf-pipeline"],
    "computer": ["myos-results-analysis", "linux-loader", "windows-loader", "digital-forensics"],
    "pc": ["windows-loader", "digital-forensics"],
    "network": ["wire-toutetu"],
    "memory": ["memory-forensics-local"],
    "reverse": ["ida-reverse", "android-malware-analysis"],
    "linux": ["linux-loader"],
    "bill": ["bill-flow-analysis"],
    "mac": ["digital-forensics"],
    "cloud": ["digital-forensics"],
    "email": ["digital-forensics"],
    "database": ["digital-forensics"],
    "generic": ["digital-forensics"],
}
DOMAIN_RULES = [
    ("memory", re.compile(r"内存镜像|内存取证|内存转储|volatility|\bmemory\b|\bram\b|进程内存", re.I)),
    # 计算机取证：显式“电脑/计算机/检材三/E01”优先于 network/mobile 的泛化关键词（如“域名”“微信”）。
    ("computer", re.compile(r"计算机取证|计算机检材|电脑检材|检材三|openKylin|openkylin|\bE01\b|磁盘镜像|计算机镜像|Linux镜像|Windows镜像|电脑|计算机", re.I)),
    ("network", re.compile(r"\bpcap\b|流量|抓包|网络包|数据包|域名|\bdns\b|\bhttp\b|\bhttps\b|\bip\s*地址|\bip\b|端口|\burl\b|邮件头|无线网络", re.I)),
    ("reverse", re.compile(r"逆向|反编译|脱壳|jadx|\bida\b|\bso\b|二进制|native|汇编|加密算法|算法分析", re.I)),
    ("mobile", re.compile(r"手机|檢材二|检材二|android|安卓|\bapk\b|微信|wechat|聊天记录|便签|备忘录|联系人|短信|相册|imei|\buin\b|\bapp\b|应用数据", re.I)),
    ("bill", re.compile(r"银行流水|资金流水|账单|交易对手|快进快出|只进不出|资金对敲", re.I)),
    ("pc", re.compile(r"\bpc\b|电脑|windows|注册表|\bntuser\b|\bprefetch\b|\bevtx\b|\blnk\b|回收站|浏览器历史|用户目录|磁盘镜像|文件系统", re.I)),
]
MOBILE_HINT = re.compile(r"手机|检材二|android|安卓|\bapk\b|微信|wechat", re.I)
TASK_RULES = [
    ("credential", re.compile(r"密码|口令|密钥|秘钥|\bkey\b|\btoken\b|\bpin\b|解锁|暗号", re.I)),
    ("reverse", re.compile(r"逆向|反编译|脱壳|加密算法|算法|native|\bso\b|汇编", re.I)),
    ("timeline", re.compile(r"时间线|先后顺序|先后|先后次序|时间顺序", re.I)),
    ("date", re.compile(r"日期|时间|哪一天|什么时候|生日|纪念日|年限|年份", re.I)),
    ("count", re.compile(r"多少|数量|条数|几个|几次|几次|几位|总数", re.I)),
    ("media", re.compile(r"图片|照片|音频|视频|ocr|二维码|截图", re.I)),
    ("network", re.compile(r"\bip\b|端口|域名|\burl\b|\bdns\b|\bhttp\b|连接", re.I)),
    ("locate", re.compile(r"是什么|名称|文件名|字段|值|型号|版本|账号|号码|位置|路径|谁|哪个|哪里|有哪些|列表|清单|进程|设备名|device_name", re.I)),
]
UNKNOWN_ANSWER = re.compile(r"^\s*(UNKNOWN|未取到|待确认|未取得)\s*$", re.I)
MEANINGFUL_NEXT = re.compile(r"^\s*(?!完成\s*$|无\s*$|none\s*$).+", re.I)


@dataclass
class Plan:
    q: int
    question: str
    domain: str
    task: str
    profile: str
    profile_deep: str
    skills: list[str]
    turns: int
    budget_seconds: int
    retry_turns: int
    retry_budget: int
    complex: bool
    deep: bool
    score: int
    reasons: list[str] = field(default_factory=list)
    tool_policy: dict[str, bool] = field(default_factory=dict)
    case_overrides: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def parse_q_list(raw: str) -> list[int]:
    out: list[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a <= b:
                out.extend(range(a, b + 1))
        elif part.isdigit():
            out.append(int(part))
    return sorted(set(out))


def parse_question_file(path: Path) -> dict[int, str]:
    lines = [ln.strip() for ln in read_text(path).splitlines() if ln.strip()]
    out: dict[int, str] = {}
    for i, line in enumerate(lines, 1):
        if "|" in line:
            n, text = line.split("|", 1)
            if n.strip().isdigit():
                out[int(n.strip())] = text.strip()
                continue
        out[i] = line
    return out


def select_question_file(notes: Path, requested: list[int], explicit: str = "") -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    cands = sorted(notes.glob("questions-*.txt"))
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    matching = []
    for p in cands:
        m = re.fullmatch(r"questions-(\d+)-(\d+)\.txt", p.name)
        if not m:
            continue
        lo, hi = int(m.group(1)), int(m.group(2))
        if all(lo <= q <= hi for q in requested):
            matching.append(p)
    return matching[0] if len(matching) == 1 else None


def read_case_profile(notes: Path) -> dict[str, Any]:
    for name in ("case-profile.json", "case.json"):
        p = notes / name
        if p.exists():
            try:
                data = json.loads(read_text(p))
                return data if isinstance(data, dict) else {}
            except (OSError, ValueError):
                return {}
    return {}


def read_sidecar_qs(notes: Path, name: str) -> list[int]:
    raw = read_text(notes / name).strip()
    return parse_q_list(raw) if raw else []


def classify_domain(question: str) -> tuple[str, list[str]]:
    reasons: list[str] = []
    for domain, rx in DOMAIN_RULES:
        if rx.search(question):
            reasons.append(f"domain:{domain}")
            return domain, reasons
    reasons.append("domain:generic(default)")
    return "generic", reasons


def classify_task(question: str) -> tuple[str, list[str]]:
    for task, rx in TASK_RULES:
        if rx.search(question):
            return task, [f"task:{task}"]
    return "unknown", ["task:unknown(default)"]


def complexity(question: str, domain: str, task: str, mobile_context: bool) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    weights = {"credential": 3, "reverse": 4, "date": 2, "timeline": 2, "media": 2, "network": 2, "count": 1, "locate": 0, "unknown": 3}
    score += weights.get(task, 0)
    reasons.append(f"task_weight:{weights.get(task, 0)}")
    if domain in ("reverse", "memory", "network", "computer", "pc", "linux", "mac", "cloud", "email", "database"):
        score += 2 if domain == "reverse" else 1
        reasons.append(f"domain_weight:{domain}")
    if mobile_context and task in ("credential", "date", "timeline", "media"):
        score += 1
        reasons.append("mobile_context:+1")
    if re.search(r"加密密钥|加密秘钥|数据库密钥|解密|跨检材|关联分析|多源|证明|所有|全部", question, re.I):
        score += 2
        reasons.append("cross_source/secret:+2")
    if re.search(r"注册表|时间线|内存镜像|文件系统|多层|嵌套", question, re.I):
        score += 1
        reasons.append("artifact_complexity:+1")
    return score, reasons


def choose_tier(score: int) -> str:
    if score >= 5:
        return "deep"
    if score >= 3:
        return "complex"
    return "base"


def build_plan(q: int, question: str, notes: Path | None = None) -> Plan:
    notes = notes or Path(".")
    case = read_case_profile(notes)
    domain, d_reasons = classify_domain(question)
    if case.get("domain") in DEFAULT_PROFILES:
        domain = str(case["domain"])
        d_reasons.append("case_profile:domain")
    elif domain in ("linux", "pc", "generic") and re.search(
        r"MYOS|myos|火眼|美亚|超级取证大师", question, re.I
    ):
        domain = "computer"
        d_reasons.append("myos_mention:computer")
    task, t_reasons = classify_task(question)
    mobile_context = bool(MOBILE_HINT.search(question)) or domain == "mobile"
    score, c_reasons = complexity(question, domain, task, mobile_context)
    tier = choose_tier(score)

    case_complex = set(int(x) for x in (case.get("complex_questions") or []) if str(x).isdigit())
    case_deep = set(int(x) for x in (case.get("deep_questions") or []) if str(x).isdigit())
    side_complex = set(read_sidecar_qs(notes, "complex-questions.txt"))
    side_deep = set(read_sidecar_qs(notes, "deep-questions.txt"))
    forced_complex = q in case_complex or q in side_complex
    forced_deep = q in case_deep or q in side_deep
    if forced_deep:
        tier = "deep"
        c_reasons.append("case_override:deep")
    elif forced_complex and tier == "base":
        tier = "complex"
        c_reasons.append("case_override:complex")

    budgets = dict(DEFAULT_BUDGETS)
    if isinstance(case.get("budgets"), dict):
        for key in budgets:
            if isinstance(case["budgets"].get(key), dict):
                budgets[key].update(case["budgets"][key])
    chosen = budgets[tier]
    retry = budgets["retry"]

    profiles = dict(DEFAULT_PROFILES.get(domain, DEFAULT_PROFILES["generic"]))
    if domain == "reverse" and mobile_context:
        base_profile = profiles.get("mobile", "dfir-max")
        deep_profile = profiles.get("mobile", "dfir-max")
    else:
        base_profile = profiles.get("base", "dfir")
        deep_profile = profiles.get("deep", base_profile)
    if case.get("profile"):
        base_profile = str(case["profile"])
    if case.get("deep_profile"):
        deep_profile = str(case["deep_profile"])
    profile = deep_profile if tier == "deep" else base_profile

    skills = list(DEFAULT_SKILLS.get(domain, DEFAULT_SKILLS["generic"]))
    if domain == "reverse" and mobile_context:
        skills = list(DEFAULT_SKILLS["mobile"])
    if isinstance(case.get("skills"), list):
        skills = [str(x) for x in case["skills"] if str(x).strip()]
    elif isinstance(case.get("skills_by_domain"), dict):
        skills = [str(x) for x in case["skills_by_domain"].get(domain, skills) if str(x).strip()]

    tool_policy = {
        "myos_first": domain in ("mobile", "computer"),
        "evidence_pack": domain == "mobile",
        "raw_fallback": True,
        "ocr": task in ("media", "date", "locate"),
        "reverse_tools": domain == "reverse" or task == "reverse",
        "pcap_tools": domain == "network",
        "memory_tools": domain == "memory",
        "registry_tools": domain == "pc",
    }
    if isinstance(case.get("tools"), dict):
        tool_policy.update({str(k): bool(v) for k, v in case["tools"].items()})

    reasons = d_reasons + t_reasons + c_reasons + [f"tier:{tier}", f"profile:{profile}"]
    return Plan(
        q=q,
        question=question,
        domain=domain,
        task=task,
        profile=profile,
        profile_deep=deep_profile,
        skills=skills,
        turns=int(chosen["turns"]),
        budget_seconds=int(chosen["seconds"]),
        retry_turns=int(retry["turns"]),
        retry_budget=int(retry["seconds"]),
        complex=tier in ("complex", "deep"),
        deep=tier == "deep",
        score=score,
        reasons=reasons,
        tool_policy=tool_policy,
        case_overrides={"complex": sorted(case_complex | side_complex), "deep": sorted(case_deep | side_deep)},
    )


def _answer_line(text: str) -> str:
    for line in text.splitlines():
        m = re.match(r"^\s*(?:[-*+]\s*)?答案\s*[：:]\s*(.*)$", line)
        if m:
            return m.group(1).strip()
    return ""


def _field_line(text: str, field: str) -> str:
    for line in text.splitlines():
        m = re.match(rf"^\s*(?:[-*+]\s*)?{re.escape(field)}\s*[：:]\s*(.*)$", line)
        if m:
            return m.group(1).strip()
    return ""


def evaluate_pending(text: str) -> dict[str, Any]:
    answer = _answer_line(text)
    excluded = _field_line(text, "已排除")
    next_step = _field_line(text, "下一轮")
    success = bool(answer) and not UNKNOWN_ANSWER.match(answer)
    has_excluded = bool(excluded) and not re.fullmatch(r"无|none", excluded.strip(), re.I)
    has_next = bool(next_step) and bool(MEANINGFUL_NEXT.match(next_step))
    if success:
        status = "OK"
    elif has_excluded and not has_next:
        status = "EXHAUSTED"
    elif not answer:
        status = "NO_ANSWER"
    else:
        status = "UNKNOWN"
    return {
        "status": status,
        "answer": answer,
        "excluded": excluded,
        "next": next_step,
        "success": success,
        "has_excluded": has_excluded,
        "has_next": has_next,
    }


def plan_to_json(plan: Plan) -> str:
    return json.dumps(plan.to_dict(), ensure_ascii=False, indent=2)


def self_test() -> int:
    samples = [
        (1, "手机的 device_name 是什么？", "mobile", "locate", "dfir-myos", "base"),
        (2, "手机里嫌疑人的 PC 开机密码是什么？", "mobile", "credential", "dfir-myos", "complex"),
        (8, "微信聊天记录数据库的加密密钥是什么？", "mobile", "credential", "dfir-max", "deep"),
        (460, "请分析检材三，电脑安装的微信版本是多少？", "computer", "count", "dfir-myos", "base"),
        (457, "请分析检材三，该电脑最后一次开机时间是？", "computer", "date", "dfir-myos", "complex"),
        (459, "请分析检材三，域名dgy02.com曾保存过一个密码，该密码是多少？", "computer", "credential", "dfir-myos", "complex"),
        (11, "PC 注册表里最后登录用户是谁？", "pc", "locate", "dfir", "base"),
        (12, "pcap 中 DNS 查询了哪些域名？", "network", "network", "dfir-pcap", "complex"),
        (13, "内存镜像里的进程列表", "memory", "locate", "dfir-mem", "base"),
        (14, "APK 的加密算法是什么？", "reverse", "reverse", "dfir-max", "deep"),
        (15, "检材中的嫌疑人姓名是什么？", "generic", "locate", "dfir", "base"),
    ]
    bad = []
    for q, text, domain, task, profile, tier in samples:
        p = build_plan(q, text)
        ok = (p.domain, p.task, p.profile) == (domain, task, profile) and (
            (tier == "base" and not p.complex) or (tier == "complex" and p.complex and not p.deep) or (tier == "deep" and p.deep)
        )
        print(f"{'OK' if ok else 'FAIL'} q={q} domain={p.domain} task={p.task} profile={p.profile} score={p.score} tier={'deep' if p.deep else 'complex' if p.complex else 'base'}")
        if not ok:
            bad.append(q)
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="DFIR question router/planner")
    ap.add_argument("--question", default="")
    ap.add_argument("--q", type=int, default=0)
    ap.add_argument("--notes", default="")
    ap.add_argument("--questions-file", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    text = args.question
    if not text and args.questions_file:
        qs = parse_question_file(Path(args.questions_file))
        text = qs.get(args.q, "")
    if not text:
        print("missing --question or --questions-file", file=sys.stderr)
        return 2
    plan = build_plan(args.q, text, Path(args.notes) if args.notes else None)
    if args.json:
        print(plan_to_json(plan))
    else:
        print(f"{plan.q} | {plan.domain} | {plan.task} | {plan.profile} | {plan.turns}/{plan.budget_seconds}s | deep={plan.deep} complex={plan.complex} score={plan.score}")
        print("skills=" + ",".join(plan.skills))
        print("reasons=" + "; ".join(plan.reasons))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
