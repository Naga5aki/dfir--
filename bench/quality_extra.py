#!/usr/bin/env python3
"""Extended paired quality tasks (10 additional tasks).

Run under final MTP and no-MTP control, then merge with the 6-task suite.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime

sys.path.insert(0, r"D:\ForensicsAgent\bench")
import run_baseline as rb  # noqa: E402


def chat(payload, timeout=600):
    return rb.api("/v1/chat/completions", rb.load_key(), payload, timeout=timeout)


def base_payload(text, max_tokens):
    return {
        "messages": [{"role": "user", "content": text}],
        "max_tokens": max_tokens, "temperature": 0.0, "top_p": 1.0,
        "top_k": 0, "min_p": 0.0, "seed": 42, "cache_prompt": False,
        "stream": False, "ignore_eos": False, "timings_per_token": False,
        "reasoning_budget_tokens": 2048,
        "chat_template_kwargs": {"enable_thinking": True, "reasoning_effort": "xhigh"},
    }


def score_number(content, expected):
    nums = re.findall(r"\\boxed\{([^}]*)\}", content)
    cand = nums[-1] if nums else ""
    ok = expected in cand or expected in content
    return (1 if ok else 0), {"expected": expected, "boxed": cand}


def score_code(content, tests, fname):
    m = re.search(r"```python\s*(.*?)```", content, re.S)
    if not m:
        return 0, {"reason": "no_python_block"}
    code = m.group(1)
    bad = ["import os", "import sys", "subprocess", "socket", "shutil", "pathlib",
           "open(", "eval(", "exec(", "__import__", "os.", "sys."]
    if any(b in code for b in bad):
        return 0, {"reason": "unsafe_or_unexpected_code", "code_head": code[:300]}
    tmp = tempfile.mkdtemp(prefix="qextra_")
    path = os.path.join(tmp, "candidate.py")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(code + "\n\n" + tests + "\nprint('PASS')\n")
        p = subprocess.run([sys.executable, "-I", path], cwd=tmp,
                           capture_output=True, text=True, timeout=10)
        ok = p.returncode == 0 and "PASS" in p.stdout
        return (1 if ok else 0), {"returncode": p.returncode,
                                  "stdout_tail": p.stdout[-300:],
                                  "stderr_tail": p.stderr[-300:],
                                  "code_head": code[:300]}
    except Exception as e:
        return 0, {"reason": repr(e), "code_head": code[:300]}
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def score_exact(content, required):
    missing = [s for s in required if s not in content]
    return (1 if not missing else 0), {"required": required, "missing": missing}


def score_tool_json(content):
    txt = content.strip()
    m = re.search(r"```json\s*(.*?)```", txt, re.S)
    if m:
        txt = m.group(1).strip()
    try:
        obj = json.loads(txt)
    except Exception as e:
        return 0, {"reason": f"json_parse: {e}", "head": txt[:300]}
    args = obj.get("arguments", {})
    ok = (obj.get("tool") == "search" and args.get("query") == "evidence"
          and int(args.get("limit", -1)) == 3)
    return (1 if ok else 0), {"object": obj}


def build_marker_prompt(target=48000):
    mt = "2026-10-30T23:59:59+08:00"
    mh = "deadbeefcafebabe"
    base = 900001
    unit = max(1, rb.token_count(rb.load_key(), rb.para(base)))
    n = max(1, round(target / unit))
    marker = (f"样本编号 Z9Q7，采集时间 {mt}，证据文件 evidence_Z9Q7.bin，"
              f"SHA-256 前缀 {mh}。")
    instr = "请只回答：样本 Z9Q7 的采集时间和 SHA-256 前缀是什么？"
    def compose(k):
        return ("本次请求编号 qextra-longctx。\n"
                + "".join(rb.para(base + j) for j in range(k))
                + marker + "\n" + instr)
    text = compose(n)
    for _ in range(4):
        nt = rb.token_count(rb.load_key(), text)
        if abs(nt - target) <= 250:
            break
        n = max(1, n + round((target - nt) / unit))
        text = compose(n)
    return text, mt, mh


def tasks():
    code_pal = (
        "assert is_palindrome('A man, a plan, a canal: Panama') == True\n"
        "assert is_palindrome('race a car') == False\n"
        "assert is_palindrome('') == True\n"
        "assert is_palindrome('0P') == False\n"
    )
    code_vow = (
        "assert count_vowels('Hello World') == 3\n"
        "assert count_vowels('AEIOU') == 5\n"
        "assert count_vowels('xyz') == 0\n"
    )
    code_bs = (
        "assert binary_search([1,3,5,7,9], 5) == 2\n"
        "assert binary_search([1,3,5,7,9], 1) == 0\n"
        "assert binary_search([1,3,5,7,9], 10) == -1\n"
        "assert binary_search([], 1) == -1\n"
    )
    text48, mt, mh = build_marker_prompt(48000)
    return [
        {"id": "math_phi1024", "category": "math",
         "prompt": "求 1024 的欧拉函数 φ(1024)。给出质因数分解和最终整数答案。",
         "max_tokens": 2048, "score": lambda c: score_number(c, "512")},
        {"id": "math_zeros100", "category": "math",
         "prompt": "求 100! 十进制末尾有多少个零。给出公式和最终整数答案。",
         "max_tokens": 2048, "score": lambda c: score_number(c, "24")},
        {"id": "math_pow7", "category": "math",
         "prompt": "求 7^2026 mod 1000 的值。给出推导和最终整数答案。",
         "max_tokens": 3072, "score": lambda c: score_number(c, "649")},
        {"id": "code_palindrome", "category": "code",
         "prompt": ("写一个 Python 函数 is_palindrome(s)，忽略大小写和非字母数字字符，"
                    "回文返回 True，否则 False。只输出一个 ```python 代码块。"),
         "max_tokens": 1536,
         "score": lambda c: score_code(c, code_pal, "is_palindrome")},
        {"id": "code_count_vowels", "category": "code",
         "prompt": ("写一个 Python 函数 count_vowels(s)，统计字符串中 a/e/i/o/u 的数量，"
                    "不区分大小写。只输出一个 ```python 代码块。"),
         "max_tokens": 1536,
         "score": lambda c: score_code(c, code_vow, "count_vowels")},
        {"id": "code_binary_search", "category": "code",
         "prompt": ("写一个 Python 函数 binary_search(arr, target)，在升序列表中返回目标下标，"
                    "找不到返回 -1。只输出一个 ```python 代码块。"),
         "max_tokens": 1536,
         "score": lambda c: score_code(c, code_bs, "binary_search")},
        {"id": "evidence_latest2", "category": "chinese_evidence",
         "prompt": ("证据表：\n"
                    "A: 2026-10-30T09:00:00+08:00, SHA-256 前缀 aa11\n"
                    "B: 2026-10-30T12:30:00+08:00, SHA-256 前缀 bb22\n"
                    "C: 2026-10-30T10:30:00+08:00, SHA-256 前缀 cc33\n"
                    "D: 2026-10-30T11:15:00+08:00, SHA-256 前缀 dd44\n"
                    "问：最晚的采集时间和哈希前缀是什么？只回答这两个字段。"),
         "max_tokens": 512,
         "score": lambda c: score_exact(c, ["2026-10-30T12:30:00+08:00", "bb22"])},
        {"id": "evidence_pid_port", "category": "chinese_evidence",
         "prompt": ("证据表：\n"
                    "S1: PID 4242, 端口 8095\n"
                    "S2: PID 5151, 端口 443\n"
                    "S3: PID 6262, 端口 8443\n"
                    "问：S2 的 PID 和端口是什么？只回答这两个字段。"),
         "max_tokens": 512,
         "score": lambda c: score_exact(c, ["5151", "443"])},
        {"id": "json_tool", "category": "structured",
         "prompt": ("仅输出 JSON，不要解释：tool=search，arguments.query=evidence，"
                    "arguments.limit=3。字段名必须是 tool、arguments；arguments 内是 query、limit。"),
         "max_tokens": 512, "score": score_tool_json},
        {"id": "longctx_48k", "category": "long_context",
         "prompt": text48, "max_tokens": 256,
         "score": lambda c, mt=mt, mh=mh: score_exact(c, [mt, mh])},
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-prefix", required=True)
    args = ap.parse_args()
    key = rb.load_key()
    out_dir = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(out_dir, args.out_prefix + "_raw.jsonl")
    summary_path = os.path.join(out_dir, args.out_prefix + "_summary.json")
    records = []
    with open(raw_path, "w", encoding="utf-8") as f:
        for t in tasks():
            if not rb.wait_idle(key, timeout=120):
                print("busy; stop", flush=True)
                break
            payload = base_payload(t["prompt"], t["max_tokens"])
            t0 = time.perf_counter()
            try:
                r = chat(payload, timeout=600)
            except Exception as e:
                rec = {"id": t["id"], "category": t["category"], "error": repr(e)}
                records.append(rec)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                print(t["id"], "ERROR", repr(e), flush=True)
                continue
            wall = time.perf_counter() - t0
            ch = r.get("choices", [{}])[0]
            msg = ch.get("message", {}) or {}
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning_content") or ""
            usage = r.get("usage", {})
            tim = r.get("timings", {})
            score, detail = t["score"](content)
            rec = {"id": t["id"], "category": t["category"],
                   "timestamp": datetime.now().isoformat(timespec="seconds"),
                   "prompt_tokens": usage.get("prompt_tokens"),
                   "completion_tokens": usage.get("completion_tokens"),
                   "finish_reason": ch.get("finish_reason"),
                   "decode_tps": tim.get("predicted_per_second"),
                   "wall_s": round(wall, 3),
                   "reasoning_chars": len(reasoning),
                   "score": score, "detail": detail, "content": content}
            records.append(rec)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{t['id']}: score={score} gen={rec['completion_tokens']} "
                  f"decode={rec['decode_tps']} wall={rec['wall_s']} finish={rec['finish_reason']}", flush=True)
    total = len([r for r in records if "error" not in r])
    passed = sum(r.get("score", 0) for r in records)
    summary = {"generated_at": datetime.now().isoformat(timespec="seconds"),
               "out_prefix": args.out_prefix, "tasks": total, "passed": passed,
               "accuracy": (passed / total) if total else None, "records": records}
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nSUMMARY {passed}/{total} accuracy={summary['accuracy']}")


if __name__ == "__main__":
    main()
