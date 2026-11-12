#!/usr/bin/env python
"""手机取证金标评测：读 pending-<题号>.md 的答案，与 gold JSON 比对。

用法：
  python eval_gold.py                       # 评测 11-20 全部
  python eval_gold.py --questions 11,12     # 只评测指定题
  python eval_gold.py --gold <路径> --notes <目录>

输出：
  - 终端表格：题号 / 判定 / 已答 / 用时 / 轮次（轮次由 _solve.log 提供，缺失则为空）
  - JSON：D:\\ForensicsAgent\\hermes\\state\\eval_runs\\<时间戳>.json

判定口径（三指标同时看，用来防止"牺牲一项换另一项"）：
  正确数 correct / 总题数 total
  单题用时 elapsed（来自 _solve.log）
  上下文压缩次数（由 eval 脚本之外核对；此处只标 missing）
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

NOTES_DIR = Path(r"D:\forensics\cases\notes")
RUNS_DIR = Path(r"D:\ForensicsAgent\hermes\state\eval_runs")
# 金标放在模型工作目录之外：模型曾读到 notes\gold-11-20.json 的 hint 直接照抄，评测失效
DEFAULT_GOLD = Path(r"D:\ForensicsAgent\hermes\state\eval\gold-11-20.json")
CASE_ROOT = Path(r"D:\forensics\cases")
SOLVE_LOG = NOTES_DIR / "_solve.log"

MOBILE_REQUIRED = {1, 3, 4, 5, 6, 7, 8}
COMPUTER_REQUIRED = {1, 2, 6, 7, 8, 9, 10}
PAPER_SECONDS = {"mobile": 2700, "computer": 3600}
QUESTION_SECONDS = 720

ANSWER_RE = re.compile(r"^[\s>*\-]*答案\s*[：:]\s*(.+?)\s*$", re.M)
UNKNOWN_TOKENS = ("UNKNOWN", "未取到", "待确认", "不确定", "N/A", "空", "unknown")
TRAILING = "。；;,，. )）]】"


def norm(value: str) -> str:
    s = (value or "").strip().strip(TRAILING).strip()
    s = s.replace(" ", "")
    return s


def strip_units(s: str) -> str:
    for unit in ("条", "元", "个", "位"):
        if s.endswith(unit):
            s = s[:-1]
    return s


def match(candidate: str, accept_list) -> bool:
    c = norm(candidate)
    if not c:
        return False
    for a in accept_list:
        t = norm(a)
        if not t:
            continue
        if c.lower() == t.lower():
            return True
        if c.lower() == strip_units(c).lower() and strip_units(c).lower() == t.lower():
            return True
        # 长串（URL / 包名 / 时间戳）允许候选带前缀说明
        if len(t) >= 8 and (c.lower().startswith(t.lower()) or t.lower() in c.lower()):
            return True
    return False


def read_answer(question: str):
    path = NOTES_DIR / f"pending-{question}.md"
    if not path.is_file():
        return None, "missing"
    text = path.read_text(encoding="utf-8", errors="replace")
    hits = ANSWER_RE.findall(text)
    if not hits:
        return None, "no-answer-line"
    ans = hits[-1].strip()
    if any(tok.lower() in ans.lower() for tok in UNKNOWN_TOKENS):
        return ans, "unknown"
    return ans, "answered"


def gold_path_allowed(gold: Path) -> bool:
    """False when the gold file would be readable as case notes.

    D:\\forensics is a junction to G:\\Forensics on this machine, so compare
    resolved paths; a missing file never resolves through the junction.
    """
    try:
        resolved = gold.resolve()
    except OSError:
        resolved = gold
    if not gold.exists():
        parent = gold.parent
        resolved = (parent.resolve() / gold.name) if parent.exists() else gold
    roots = [CASE_ROOT]
    if CASE_ROOT.exists():
        roots.append(CASE_ROOT.resolve())
    return not any(root == resolved or root in resolved.parents for root in roots)


def paper_gate(summary: dict, paper: str) -> list[str]:
    """Return failure reasons; an empty list means the paper passed."""
    fails = []
    rows = {r["question"]: r for r in summary.get("rows", [])}
    required = MOBILE_REQUIRED if paper == "mobile" else COMPUTER_REQUIRED
    wrong = summary.get("wrong", 0)
    if wrong:
        fails.append(f"WRONG count {wrong}")
    for q, r in rows.items():
        if r["verdict"] == "WRONG":
            fails.append(f"Q{q} WRONG")
        if r.get("status") == "TIMEOUT":
            fails.append(f"Q{q} TIMEOUT")
        if r.get("seconds") is None:
            fails.append(f"Q{q} seconds missing")
        elif r["seconds"] > QUESTION_SECONDS:
            fails.append(f"Q{q} {r['seconds']}s exceeds {QUESTION_SECONDS}s")
    for q in required:
        verdict = rows.get(q, {}).get("verdict")
        if verdict != "OK":
            fails.append(f"Q{q} required OK, got {verdict}")
    if paper == "computer" and rows.get(3, {}).get("verdict") not in ("OK", "UNKNOWN"):
        fails.append(f"Q3 must be OK or UNKNOWN, got {rows.get(3, {}).get('verdict')}")
    elapsed = summary.get("elapsed_seconds", 0)
    if elapsed > PAPER_SECONDS[paper]:
        fails.append(f"paper {elapsed}s exceeds {PAPER_SECONDS[paper]}s")
    return fails


def read_timings():
    """从 _solve.log 读取 'Q11 | profile | 320s | OK' 这类记录。"""
    out = {}
    if not SOLVE_LOG.is_file():
        return out
    # PowerShell Tee-Object 默认写 UTF-16LE，历史上也写过 UTF-8：两种都试
    raw = SOLVE_LOG.read_bytes()
    text = raw.decode('utf-16', 'replace') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') or raw[1:2] == b'\x00' else raw.decode('utf-8', 'replace')
    for line in text.splitlines():
        line = line.replace('\x00', '').strip()
        # 兼容两种格式：旧 "Q11 | profile | 320s | OK" 与现行 "Q11 | profile | 320s | OK | attempt=1 | 时间戳"
        m = re.match(r"^Q(\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+)s\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            status = m.group(4).split('|')[0].strip()
            out[m.group(1)] = {"profile": m.group(2).strip(), "seconds": int(m.group(3)),
                               "status": status}
    return out


def main() -> int:
    global NOTES_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default=str(DEFAULT_GOLD))
    ap.add_argument("--notes", default=str(NOTES_DIR))
    ap.add_argument("--questions", default="")
    args = ap.parse_args()

    notes = Path(args.notes)
    NOTES_DIR = notes

    gold_path = Path(args.gold)
    if not gold_path_allowed(gold_path):
        print("gold 不在允许路径", file=sys.stderr)
        return 2
    if not gold_path.is_file():
        print(f"gold 不存在: {gold_path}", file=sys.stderr)
        return 2
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    qs = gold["questions"]
    wanted = [q.strip() for q in args.questions.split(",") if q.strip()] or sorted(qs, key=int)
    timings = read_timings()

    rows, correct, answered, unknown, missing = [], 0, 0, 0, 0
    for q in wanted:
        spec = qs.get(q)
        if not spec:
            continue
        ans, state = read_answer(q)
        if state == "missing":
            missing += 1
            verdict = "MISSING"
        elif state == "no-answer-line":
            missing += 1
            verdict = "NO-LINE"
        elif state == "unknown":
            unknown += 1
            verdict = "UNKNOWN"
        else:
            answered += 1
            verdict = "OK" if match(ans, spec.get("accept") or [spec["answer"]]) else "WRONG"
            if verdict == "OK":
                correct += 1
        t = timings.get(q, {})
        rows.append({
            "question": int(q),
            "verdict": verdict,
            "answer": ans,
            "gold": spec["answer"],
            "verified": bool(spec.get("verified", False)),
            "seconds": t.get("seconds"),
            "profile": t.get("profile"),
        })

    total = len(rows)
    wrong = sum(1 for r in rows if r["verdict"] == "WRONG")
    summary = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "gold": str(gold_path),
        "total": total,
        "correct": correct,
        "answered": answered,
        "unknown": unknown,
        "missing": missing,
        "wrong": wrong,
        "correct_rate": round(correct / total, 3) if total else 0.0,
        "elapsed_seconds": sum(r["seconds"] or 0 for r in rows),
        "rows": rows,
    }

    print(f"{'题':>3} {'判定':<8} {'用时':>6} {'答案':<28} {'金标':<28}")
    for r in rows:
        sec = f"{r['seconds']}s" if r["seconds"] else "-"
        flag = "" if r["verified"] else " (待校验)"
        print(f"{r['question']:>3} {r['verdict']:<8} {sec:>6} {str(r['answer'])[:26]:<28} "
              f"{r['gold'][:24]:<28}{flag}")
    print(f"\n正确 {correct}/{total}  已答 {answered}  未取到 {unknown}  缺失 {missing}  "
          f"总用时 {summary['elapsed_seconds']}s")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out = RUNS_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
