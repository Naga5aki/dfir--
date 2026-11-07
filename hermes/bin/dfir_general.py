#!/usr/bin/env python3
"""Case-agnostic DFIR runner built on dfir_plan.

The runner is intentionally separate from the validated 2025fic PowerShell
script. It supports any case/domain selected by the planner, one process per
question, bounded retries, pending-based verdicts, an external hard wall, and a
deterministic MockAgent used by the mock benchmark.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dfir_plan  # noqa: E402

TOOL_BLOCKED_RE = re.compile(
    r"(?i)(?:tool|mcp|sqlite|terminal|read_file|write_file)[^\r\n]{0,140}"
    r"(?:not authorized|not a known tool name|permission denied|拒绝访问|blocked|does not exist|no such file)"
)
MAX_ITER_RE = re.compile(r"(?i)ran out of steps|max_iterations|maximum number of iterations")
UNKNOWN_WORDS = re.compile(r"^\s*(UNKNOWN|未取到|待确认|未取得)\s*$", re.I)


@dataclass
class AgentResult:
    returncode: int = 0
    timed_out: bool = False
    log: str = ""


class Agent:
    def run(self, plan: dfir_plan.Plan, prompt_file: Path, log_file: Path, case_root: Path) -> AgentResult:
        raise NotImplementedError


class HermesAgent(Agent):
    def __init__(self, command: str = "hermes", extra: list[str] | None = None):
        self.command = command
        self.extra = extra or []

    def _argv(self, plan: dfir_plan.Plan, prompt_file: Path, case_root: Path) -> list[str]:
        argv = shlex.split(self.command, posix=False)
        argv += ["-p", plan.profile, "chat", "--query-file", str(prompt_file),
                 "--oneshot", "-Q", "--yolo", "--max-turns", str(plan.turns),
                 "--run-budget", str(plan.budget_seconds)]
        if plan.skills:
            argv += ["-s", ",".join(plan.skills)]
        argv += ["--in", str(case_root)]
        argv += self.extra
        return argv

    def run(self, plan, prompt_file, log_file, case_root):
        argv = self._argv(plan, prompt_file, case_root)
        # A .cmd/.bat needs cmd.exe on Windows; hermes.exe/hermes is direct.
        use_shell = bool(argv and argv[0].lower().endswith((".cmd", ".bat"))) and os.name == "nt"
        if use_shell:
            argv = ["cmd.exe", "/d", "/c"] + argv
        with log_file.open("w", encoding="utf-8", errors="replace") as fh:
            proc = subprocess.Popen(argv, cwd=str(case_root), stdout=fh, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            timed_out = False
            try:
                proc.wait(timeout=plan.budget_seconds + 60)
            except subprocess.TimeoutExpired:
                timed_out = True
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        return AgentResult(returncode=proc.returncode if proc.returncode is not None else -1,
                           timed_out=timed_out, log=read_text(log_file))


class MockAgent(Agent):
    """Deterministic agent for the mock benchmark; never reads real evidence."""

    def __init__(self, scenarios: dict[int, str] | None = None):
        self.scenarios = scenarios or {}
        self.calls: dict[int, int] = {}

    def run(self, plan, prompt_file, log_file, case_root):
        n = self.calls.get(plan.q, 0) + 1
        self.calls[plan.q] = n
        scenario = self.scenarios.get(plan.q, "success")
        if scenario == "retry_success":
            scenario = "success" if n >= 2 else "unknown_next"
        pending = Path(prompt_file).parent / f"pending-{plan.q}.md"
        log = f"mock scenario={scenario} q={plan.q} attempt={n}\n"
        if scenario == "success":
            pending.write_text(
                f"题{plan.q}（mock）\n答案：MOCK-ANSWER\n证据：mock:\\case\\raw.json field=value\n"
                "已排除：候选A无该字段\n下一轮：完成\n", encoding="utf-8")
        elif scenario == "unknown_next":
            pending.write_text(
                f"题{plan.q}（mock）\n答案：UNKNOWN\n证据：已定位 mock 表，缺终值\n"
                "已排除：无\n下一轮：查询 mock 候选字段\n", encoding="utf-8")
        elif scenario == "exhausted":
            pending.write_text(
                f"题{plan.q}（mock）\n答案：UNKNOWN\n证据：已定位 mock 表\n"
                "已排除：候选A、候选B\n下一轮：完成\n", encoding="utf-8")
        elif scenario == "tool_blocked":
            log += "tool error: not authorized\n"
        elif scenario == "budget":
            log += "agent ran out of steps: max_iterations\n"
        elif scenario == "no_answer":
            log += "no pending written\n"
        elif scenario == "timeout":
            return AgentResult(returncode=-1, timed_out=True, log=log + "mock timeout\n")
        log_file.write_text(log, encoding="utf-8")
        return AgentResult(returncode=0, timed_out=False, log=log)


PY312 = Path(r"C:\Users\TWK\AppData\Local\Programs\Python\Python312\python.exe")
PY_MCP = Path(r"C:\Users\TWK\AppData\Local\Python\pythoncore-3.14-64\python.exe")


def bootstrap(case_root: Path, notes: Path, skip_myos: bool = False, mount: bool = False) -> None:
    """Best-effort case bootstrap; never fatal. Mount is explicit opt-in."""
    if mount:
        for script, args in (("myos_mount.py", ["mount"]), ("myos_appmap.py", [])):
            exe = Path(__file__).resolve().parent / script
            if exe.exists() and PY312.exists():
                try:
                    subprocess.run([str(PY312), "-I", str(exe), *args], cwd=str(case_root),
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=240)
                except Exception as exc:
                    print(f"bootstrap warning: {script}: {type(exc).__name__}", file=sys.stderr)
    if not skip_myos:
        helper = Path(__file__).resolve().parent / "myos_compact.py"
        if helper.exists() and PY_MCP.exists():
            try:
                subprocess.run([str(PY_MCP), "-I", str(helper), "--notes", str(notes)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
            except Exception as exc:
                print(f"bootstrap warning: myos_compact: {type(exc).__name__}", file=sys.stderr)


def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def sig(path: Path) -> str:
    if not path.exists():
        return "absent"
    st = path.stat()
    return f"{st.st_mtime_ns}-{st.st_size}"


def fallback_pending(q: int, verdict: str, pending: Path, log_file: Path) -> None:
    if pending.exists() and read_text(pending).strip():
        return
    reason = {
        "TOOL_BLOCKED": "核对当前 case/mount 与工具 dbPath；修复授权/工具名后重跑",
        "BUDGET_EXHAUSTED": "读取日志最后有效输出；缩小到一个具体查询后重跑",
        "TIMEOUT": "读取日志末尾；下一次只做最小成本查询",
        "EXHAUSTED": "按已排除分支换数据源",
        "NO_QUESTION": "补齐本题题干后重跑",
    }.get(verdict, "检查日志；按具体线索单独重跑")
    pending.write_text(
        f"题{q}（自动收口：{verdict}）\n答案：UNKNOWN\n"
        f"证据：未取得可核验原始字段；最后日志：{log_file.name}\n"
        f"已排除：{verdict}（自动判定）\n下一轮：{reason}\n", encoding="utf-8")


def prompt_for(plan: dfir_plan.Plan, case_root: Path, notes: Path, pack: Path | None) -> str:
    myos = notes / "device_map.myos.summary.txt"
    device_map = notes / "device_map.summary.txt"
    computer = notes / "device_map.computer.summary.txt"
    hints = notes / "case-hints.md"
    evidence = [str(p) for p in (pack if pack and pack.exists() else None,
                                 myos if myos.exists() else None,
                                 device_map if device_map.exists() else None,
                                 computer if computer.exists() else None) if p]
    evidence_block = "\n".join(f"- {p}" for p in evidence) or "- 先枚举当前案件的真实数据源，不要猜路径"
    domain_hint = {
        "mobile": "手机取证：优先 MYOS 紧凑索引/device_map，再查 appMfsPath 的 .mfs；明文库用 dbq.py；图片用 OCR，不要 read_file。",
        "computer": "计算机取证：先读 notes/device_map.computer.summary.txt；用 computer_keyword_search.py 从题面抽哈希/手机号/域名/实体并做有界命中；插件库 .mfs 用 sqlite_query（先 sqlite_master 再一条有界 SELECT）；原始盘走 query_device_mount_path；嵌套 VM（*.vmdk）用 myos_nested_vm.py 只读注册/挂载；浏览器密码用 chrome_login_decrypt.py；不要重读 70KB 概览或全量 grep 13GB。",
        "pc": "PC 取证：优先注册表、事件日志、文件系统、浏览器/回收站/LNK 等原始证据；按 windows-loader 技能取数。",
        "network": "网络取证：优先 PCAP/会话/协议字段；先确认文件类型与时间范围，再做有界过滤。",
        "memory": "内存取证：先确认镜像类型与 profile，再做进程/网络/凭据等有界查询。",
        "reverse": "逆向：先确认 APK/SO/二进制类型，按 jadx/IDA 等技能；先定位入口和字符串，再验证算法。",
        "linux": "Linux 取证：优先 /var/log、systemd journal、bash_history、SSH 配置与文件系统；按 linux-loader 技能取数。",
        "mac": "macOS 取证：优先 plist、Keychain、APFS/HFS 元数据、Spotlight/iMessage；确认加密卷状态。",
        "cloud": "云取证：先确认云厂商/对象存储/租户与时间范围，再做有界列举；不要把本地缓存当云端原始数据。",
        "email": "邮件取证：先确认 EML/PST/MSG/MIME 类型，提取头字段、时间、附件哈希；正文和附件分离处理。",
        "database": "数据库取证：先确认数据库类型与文件状态（含 WAL/日志），只读打开；先查 schema 再查行。",
        "generic": "通用取证：先确认检材类型与时间范围，再选最小可验证数据源。",
    }[plan.domain]
    return f"""题面（第 {plan.q} 题）：{plan.question}

只回答这一题，不要回答其他题。

案件根：{case_root}
本题计划：domain={plan.domain} task={plan.task} profile={plan.profile} skills={','.join(plan.skills) or '无'} 预算={plan.turns}次工具迭代/{plan.budget_seconds}秒
证据入口（只读）：
{evidence_block}
案件提示（可选，只读）：{hints if hints.exists() else '无'}

硬性规则：
0. 先读证据入口和案件提示；不要从 `ls data/data`、全量枚举或猜包名/表名开始。
1. {domain_hint}
2. 取数使用现成脚本/工具；包名、库名、表名、列名必须来自索引或实际枚举。`.mfs` 用 MCP sqlite_query；明文库用 dbq.py。
3. 第 {max(2, plan.turns // 3)} 次工具迭代前先写一次 {notes}\\pending-{plan.q}.md 占位（答案 UNKNOWN），之后每拿到关键字段就覆盖更新；覆盖前先读当前文件。
4. 答案格式：
题{plan.q}（一句话题意）
答案：<符合题面格式的最终值>
证据：<root 相对路径 + 表/文件 + 关键字段=值>
已排除：<错误分支；没有写 无>
下一轮：完成 / <具体下一步>
5. 不确定就写 UNKNOWN；“证据”必须给出已定位库/表/文件 + 已见候选 + 还差哪一步；不要编造，不要把题面示例当答案。
6. 出现新证据、缩小候选、排除具体假设、修复工具错误才继续；连续 2 次工具迭代无新增证据，或同一工具连续 2 次失败且无修复路径，立即收口并停止。
7. 剩余预算不足以完成下一项高成本操作时先落盘。证据只读，禁止写入检材目录。
8. `notes` 目录内只读本题 evidence/pending/device_map/myos/case-hints；禁止读其它 pending、_solve 日志、findings、gold/eval 或参考答案。检材原始数据只读访问不受此限。
"""


def run_question(plan: dfir_plan.Plan, text: str, case_root: Path, notes: Path, agent: Agent,
                 skip_pack: bool = False, retry: bool = True) -> dict:
    pack = notes / f"evidence-q{plan.q}.txt"
    if plan.tool_policy.get("evidence_pack") and not skip_pack:
        ep = Path(__file__).resolve().parent / "evidence_pack.py"
        if ep.exists():
            subprocess.run([sys.executable, "-I", str(ep), "--q", str(plan.q), "--text", text,
                            "--out", str(pack)], cwd=str(case_root), stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    pending = notes / f"pending-{plan.q}.md"
    if pending.exists():
        previous = dfir_plan.evaluate_pending(read_text(pending))
        if previous["success"]:
            return {"q": plan.q, "domain": plan.domain, "task": plan.task, "profile": plan.profile,
                    "tier": "deep" if plan.deep else "complex" if plan.complex else "base",
                    "attempt": 0, "seconds": 0, "verdict": "SKIP_ANSWERED"}
        prev_dir = notes / "prev"
        prev_dir.mkdir(parents=True, exist_ok=True)
        pending.replace(prev_dir / f"pending-{plan.q}.{datetime.now():%Y%m%d-%H%M%S}.md")
    prompt_file = notes / f"_solve-q{plan.q}.prompt.txt"
    total = 0
    attempt = 0
    verdict = "FAILED"
    current = plan
    while attempt < (2 if retry else 1) and verdict not in ("OK", "EXHAUSTED", "TOOL_BLOCKED", "BUDGET_EXHAUSTED", "TIMEOUT"):
        attempt += 1
        before = sig(pending)
        prompt_file.write_text(prompt_for(current, case_root, notes, pack), encoding="utf-8")
        log_file = notes / f"_solve-q{plan.q}-a{attempt}.log"
        started = time.monotonic()
        result = agent.run(current, prompt_file, log_file, case_root)
        total += int(time.monotonic() - started)
        pending_text = read_text(pending)
        after = sig(pending)
        evaluated = dfir_plan.evaluate_pending(pending_text)
        if after != before and evaluated["success"]:
            verdict = "OK"
            break
        log = result.log or read_text(log_file)
        if result.timed_out:
            verdict = "TIMEOUT"
        elif TOOL_BLOCKED_RE.search(log):
            verdict = "TOOL_BLOCKED"
        elif evaluated["has_excluded"] and not evaluated["has_next"]:
            verdict = "EXHAUSTED"
        elif MAX_ITER_RE.search(log) and not evaluated["has_next"]:
            verdict = "BUDGET_EXHAUSTED"
        elif attempt == 1 and evaluated["has_next"]:
            verdict = "FAILED"
            current = dfir_plan.Plan(**{**current.to_dict(), "turns": current.retry_turns,
                                        "budget_seconds": current.retry_budget})
        else:
            verdict = "FAILED" if evaluated["status"] != "UNKNOWN" else "UNKNOWN"
            break
    if verdict != "OK":
        fallback_pending(plan.q, verdict, pending, notes / f"_solve-q{plan.q}-a{attempt}.log")
    return {"q": plan.q, "domain": plan.domain, "task": plan.task, "profile": plan.profile,
            "tier": "deep" if plan.deep else "complex" if plan.complex else "base",
            "attempt": attempt, "seconds": total, "verdict": verdict}


def select_questions(notes: Path, spec: str, explicit: str) -> tuple[Path | None, list[int], dict[int, str]]:
    qs = dfir_plan.parse_q_list(spec) if spec else []
    qfile = dfir_plan.select_question_file(notes, qs or [1], explicit)
    if not qfile:
        return None, qs, {}
    texts = dfir_plan.parse_question_file(qfile)
    if not qs:
        qs = sorted(texts)
    return qfile, qs, texts


def solve_case(case_root: Path, questions: str, questions_file: str, agent: Agent,
               dry_run: bool = False, batch_budget: int = 0, skip_pack: bool = False,
               skip_myos: bool = False, mount: bool = False) -> list[dict]:
    case_root = case_root.resolve()
    notes = case_root / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    if not dry_run:
        bootstrap(case_root, notes, skip_myos=skip_myos, mount=mount)
    qfile, qs, texts = select_questions(notes, questions, questions_file)
    if not qfile:
        raise SystemExit("cannot select questions-*.txt (use --questions-file)")
    if not qs:
        raise SystemExit("no questions selected")
    plans = []
    for q in qs:
        text = texts.get(q, "")
        if not text:
            plans.append(None)
            continue
        plans.append(dfir_plan.build_plan(q, text, notes))
    if dry_run:
        for p in plans:
            if p:
                print(f"Q{p.q} | {p.domain} | {p.task} | {p.profile} | {p.turns}/{p.budget_seconds}s | skills={','.join(p.skills)}")
        return []
    start = time.monotonic()
    results = []
    log_path = notes / "_solve.log"
    for p in plans:
        if p is None:
            continue
        if batch_budget and time.monotonic() - start >= batch_budget:
            (notes / "_batch_budget_stop.md").write_text(
                f"Batch budget exhausted at Q{p.q}; remaining: {','.join(str(x.q) for x in plans if x and x.q >= p.q)}\n",
                encoding="utf-8")
            break
        res = run_question(p, p.question, case_root, notes, agent, skip_pack=skip_pack)
        results.append(res)
        line = f"Q{p.q} | {p.profile} | {p.domain}/{p.task} | {res['seconds']}s | {res['verdict']} | attempt={res['attempt']} | {datetime.now():%Y-%m-%d %H:%M:%S}"
        print(line)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Case-agnostic DFIR runner")
    ap.add_argument("--case-root", required=True)
    ap.add_argument("--questions", default="")
    ap.add_argument("--questions-file", default="")
    ap.add_argument("--hermes", default="hermes")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch-budget", type=int, default=0)
    ap.add_argument("--skip-pack", action="store_true")
    ap.add_argument("--skip-myos", action="store_true", help="do not refresh device_map.myos.*")
    ap.add_argument("--mount", action="store_true", help="opt in to MYOS mount + appmap before the batch")
    ap.add_argument("--mock-scenarios", default="", help="JSON q->scenario for internal mock mode")
    args = ap.parse_args()
    if args.mock_scenarios:
        scenarios = {int(k): str(v) for k, v in json.loads(args.mock_scenarios).items()}
        agent = MockAgent(scenarios)
    else:
        agent = HermesAgent(args.hermes)
    try:
        solve_case(Path(args.case_root), args.questions, args.questions_file, agent,
                   dry_run=args.dry_run, batch_budget=args.batch_budget, skip_pack=args.skip_pack,
                   skip_myos=args.skip_myos, mount=args.mount)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
