#!/usr/bin/env python3
"""Small, verifiable quality probes against the running server.

Not a quality regression suite. It checks:
  1. whether the 2048 reasoning budget truncates a hard, verifiable task;
  2. whether a unique fact near the end of a ~55K-token prompt is retrievable.

Read-only: no server configuration changes, no external uploads.
"""
import json
import sys
import time
import urllib.request
from datetime import datetime

sys.path.insert(0, r"D:\ForensicsAgent\bench")
import run_baseline as rb  # noqa: E402

BASE = "http://127.0.0.1:8095"
KEY = rb.load_key()


def chat(payload, timeout=900):
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read().decode("utf-8"))
    return out, time.perf_counter() - t0


def base_payload(text, max_tokens, budget):
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


def run_one(label, text, max_tokens, budget, timeout=900):
    if not rb.wait_idle(KEY, timeout=120):
        return {"label": label, "error": "server busy"}
    out, wall = chat(base_payload(text, max_tokens, budget), timeout=timeout)
    ch = out.get("choices", [{}])[0]
    msg = ch.get("message", {}) or {}
    reasoning = msg.get("reasoning_content") or ""
    content = msg.get("content") or ""
    usage = out.get("usage", {})
    tim = out.get("timings", {})
    rec = {
        "label": label,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "budget_requested": budget,
        "max_tokens": max_tokens,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "cache_n": tim.get("cache_n"),
        "prompt_tps": tim.get("prompt_per_second"),
        "decode_tps": tim.get("predicted_per_second"),
        "ttft_est_s": (tim.get("prompt_ms", 0) + tim.get("predicted_per_token_ms", 0)) / 1000.0,
        "wall_s": round(wall, 3),
        "finish_reason": ch.get("finish_reason"),
        "reasoning_chars": len(reasoning),
        "content_chars": len(content),
        "reasoning_tokens": rb.token_count(KEY, reasoning) if reasoning else 0,
        "reasoning_tail": reasoning[-300:],
        "content": content,
    }
    return rec


def build_long_prompt(target=55400):
    base = 700001
    unit_tokens = max(1, rb.token_count(KEY, rb.para(base)))
    n = round(target / unit_tokens)
    marker = (
        "样本编号 Z9Q7，采集时间 2026-10-30T23:59:59+08:00，"
        "证据文件 evidence_Z9Q7.bin，SHA-256 前缀 deadbeefcafebabe。"
    )
    instruction = "请只回答：样本 Z9Q7 的采集时间和 SHA-256 前缀是什么？"
    def compose(k):
        return (f"本次请求编号 longfact-{datetime.now().strftime('%H%M%S')}。\n"
                + "".join(rb.para(base + j) for j in range(k))
                + marker + "\n" + instruction)
    text = compose(n)
    for _ in range(4):
        nt = rb.token_count(KEY, text)
        if abs(nt - target) <= 200:
            break
        n = max(1, n + round((target - nt) / unit_tokens))
        text = compose(n)
    return text, rb.token_count(KEY, text)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    math_q = (
        "求最小的正整数 n，使得 n! 的十进制表示末尾恰好有 2026 个零。"
        "请给出完整推导、关键不等式与最终整数答案。"
    )
    records = []
    for budget in (2048, 4096):
        rec = run_one(f"math_budget_{budget}", math_q, 4608, budget)
        records.append(rec)
        print(json.dumps({k: v for k, v in rec.items() if k in (
            "label", "budget_requested", "prompt_tokens", "completion_tokens",
            "reasoning_tokens", "finish_reason", "decode_tps", "wall_s")},
            ensure_ascii=False), flush=True)
        print("answer_tail:", (rec.get("content") or "")[-500:].replace("\n", " "), flush=True)
        time.sleep(2)

    text, nt = build_long_prompt()
    rec = run_one("longfact_55k", text, 128, 2048)
    rec["raw_prompt_tokens"] = nt
    records.append(rec)
    print(json.dumps({k: v for k, v in rec.items() if k in (
        "label", "prompt_tokens", "completion_tokens", "reasoning_tokens",
        "finish_reason", "decode_tps", "ttft_est_s", "wall_s")}, ensure_ascii=False), flush=True)
    print("longfact_answer:", repr(rec.get("content") or ""), flush=True)
    print("longfact_reasoning_tail:", repr((rec.get("reasoning_tail") or "")[-300:]), flush=True)

    out = rf"D:\ForensicsAgent\bench\quality_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"generated_at": datetime.now().isoformat(timespec="seconds"),
                   "records": records}, f, ensure_ascii=False, indent=2)
    print("saved:", out)


if __name__ == "__main__":
    main()
