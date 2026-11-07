#!/usr/bin/env python3
"""Compact paired quality regression for the local server.

Runs a fixed set of verifiable tasks and writes raw responses + scores.
No config changes. The same script is intended to run under:
  - final MTP config
  - no-MTP control (same 64K/ngl64/threads8/cache512)
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

BASE = "http://127.0.0.1:8095"


def chat(payload, timeout=600):
    return rb.api("/v1/chat/completions", rb.load_key(), payload, timeout=timeout)


def base_payload(text, max_tokens, budget=2048):
    return {
        "messages": [{"role": "user", "content": text}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "top_p": 1.0,
        "top_k": 0,
        "min_p": 0.0,
        "seed": 42,
        "cache_prompt": False,
        "stream": False,
        "ignore_eos": False,
        "timings_per_token": False,
        "reasoning_budget_tokens": budget,
        "chat_template_kwargs": {"enable_thinking": True, "reasoning_effort": "xhigh"},
    }


def score_math(content, expected):
    nums = re.findall(r"\\boxed\{([^}]*)\}", content)
    cand = nums[-1] if nums else ""
    if not cand:
        # fallback: last number in the final answer section
        m = re.findall(r"8120|400", content)
        cand = m[-1] if m else ""
    ok = expected in cand or expected in content
    return (1 if ok else 0), {"expected": expected, "boxed": cand}


def score_code(content):
    m = re.search(r"```python\s*(.*?)```", content, re.S)
    if not m:
        return 0, {"reason": "no_python_block"}
    code = m.group(1)
    bad = ["import os", "import sys", "subprocess", "socket", "shutil", "pathlib",
           "open(", "eval(", "exec(", "__import__", "os.", "sys."]
    if any(b in code for b in bad):
        return 0, {"reason": "unsafe_or_unexpected_code", "code_head": code[:300]}
    tests = (
        "\n\n"
        "assert merge_intervals([]) == [], 'empty'\n"
        "assert merge_intervals([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]], 'basic'\n"
        "assert merge_intervals([[1,4],[4,5]]) == [[1,5]], 'touching'\n"
        "assert merge_intervals([[1,10],[2,3]]) == [[1,10]], 'contained'\n"
        "assert merge_intervals([[5,6],[1,2]]) == [[1,2],[5,6]], 'unsorted'\n"
        "assert merge_intervals([[1,2],[3,4]]) == [[1,2],[3,4]], 'disjoint'\n"
        "print('PASS')\n"
    )
    tmp = tempfile.mkdtemp(prefix="qreg_")
    path = os.path.join(tmp, "candidate.py")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(code + tests)
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
        try:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass


def score_exact(content, required):
    missing = [s for s in required if s not in content]
    return (1 if not missing else 0), {"required": required, "missing": missing}


def score_json(content):
    txt = content.strip()
    m = re.search(r"```json\s*(.*?)```", txt, re.S)
    if m:
        txt = m.group(1).strip()
    try:
        obj = json.loads(txt)
    except Exception as e:
        return 0, {"reason": f"json_parse: {e}", "head": txt[:300]}
    ok = (obj.get("task") == "evidence_review" and obj.get("priority") == "high"
          and obj.get("evidence_ids") == ["E1", "E3"])
    return (1 if ok else 0), {"object": obj}


def build_marker_prompt(target=32000):
    marker_time = "2026-10-30T23:59:59+08:00"
    marker_hash = "deadbeefcafebabe"
    base = 800001
    unit_tokens = max(1, rb.token_count(rb.load_key(), rb.para(base)))
    n = max(1, round(target / unit_tokens))
    marker = (f"样本编号 Z9Q7，采集时间 {marker_time}，证据文件 evidence_Z9Q7.bin，"
              f"SHA-256 前缀 {marker_hash}。")
    instruction = "请只回答：样本 Z9Q7 的采集时间和 SHA-256 前缀是什么？"
    def compose(k):
        return ("本次请求编号 qreg-longctx。\n"
                + "".join(rb.para(base + j) for j in range(k))
                + marker + "\n" + instruction)
    text = compose(n)
    for _ in range(4):
        nt = rb.token_count(rb.load_key(), text)
        if abs(nt - target) <= 200:
            break
        n = max(1, n + round((target - nt) / unit_tokens))
        text = compose(n)
    return text, marker_time, marker_hash


def tasks():
    return [
        {"id": "math_zeros", "category": "math",
         "prompt": ("求最小的正整数 n，使得 n! 的十进制表示末尾恰好有 2026 个零。"
                    "请给出完整推导、关键不等式与最终整数答案。"),
         "max_tokens": 4608, "score": lambda c: score_math(c, "8120")},
        {"id": "math_phi1000", "category": "math",
         "prompt": ("求 1 到 1000 中与 1000 互质的正整数个数。"
                    "请给出质因数分解、欧拉函数计算和最终整数答案。"),
         "max_tokens": 4096, "score": lambda c: score_math(c, "400")},
        {"id": "code_merge_intervals", "category": "code",
         "prompt": ("写一个 Python 函数 merge_intervals(intervals)，合并所有重叠或接触的区间，"
                    "返回按 start 排序的列表。处理空列表、单区间、完全包含、相邻区间。"
                    "只输出一个 ```python 代码块，不要解释。"),
         "max_tokens": 2048, "score": score_code},
        {"id": "evidence_latest", "category": "chinese_evidence",
         "prompt": ("证据表：\n"
                    "A: 采集时间 2026-10-30T10:00:00+08:00, SHA-256 前缀 aa11bb22\n"
                    "B: 采集时间 2026-10-30T12:00:00+08:00, SHA-256 前缀 cc33dd44\n"
                    "C: 采集时间 2026-10-30T11:00:00+08:00, SHA-256 前缀 ee55ff66\n"
                    "问：最晚的采集时间和对应哈希前缀是什么？只回答这两个字段。"),
         "max_tokens": 512, "score": lambda c: score_exact(c, ["2026-10-30T12:00:00+08:00", "cc33dd44"])},
        {"id": "json_schema", "category": "structured",
         "prompt": ("把以下结论输出为 JSON，仅输出 JSON，不要解释："
                    "任务=evidence_review，优先级=high，证据编号=[\"E1\",\"E3\"]。"
                    "字段名必须是 task, priority, evidence_ids。"),
         "max_tokens": 512, "score": score_json},
        {"id": "longctx_32k", "category": "long_context",
         "prompt": None, "max_tokens": 256,
         "score": None},  # filled below
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-prefix", required=True)
    args = ap.parse_args()
    key = rb.load_key()
    ts = tasks()

    text32, marker_time, marker_hash = build_marker_prompt(32000)
    for t in ts:
        if t["id"] == "longctx_32k":
            t["prompt"] = text32
            t["score"] = lambda c, mt=marker_time, mh=marker_hash: score_exact(c, [mt, mh])
            t["prompt_tokens_hint"] = rb.token_count(key, text32)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(out_dir, args.out_prefix + "_raw.jsonl")
    summary_path = os.path.join(out_dir, args.out_prefix + "_summary.json")
    records = []
    with open(raw_path, "w", encoding="utf-8") as f:
        for t in ts:
            if not rb.wait_idle(key, timeout=120):
                print("busy; stop", flush=True)
                break
            payload = base_payload(t["prompt"], t["max_tokens"], 2048)
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
            rec = {
                "id": t["id"], "category": t["category"],
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "finish_reason": ch.get("finish_reason"),
                "decode_tps": tim.get("predicted_per_second"),
                "wall_s": round(wall, 3),
                "reasoning_chars": len(reasoning),
                "score": score,
                "detail": detail,
                "content": content,
            }
            records.append(rec)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{t['id']}: score={score} gen={rec['completion_tokens']} "
                  f"decode={rec['decode_tps']} wall={rec['wall_s']} finish={rec['finish_reason']}", flush=True)

    total = len([r for r in records if "error" not in r])
    passed = sum(r.get("score", 0) for r in records)
    summary = {"generated_at": datetime.now().isoformat(timespec="seconds"),
               "out_prefix": args.out_prefix, "tasks": total, "passed": passed,
               "accuracy": (passed / total) if total else None,
               "records": records}
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nSUMMARY {passed}/{total} accuracy={summary['accuracy']}")


if __name__ == "__main__":
    main()
