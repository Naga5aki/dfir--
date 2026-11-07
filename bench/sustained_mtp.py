#!/usr/bin/env python3
"""10-minute sustained single-request load for the current MTP config.

Writes raw JSONL + GPU CSV + summary. Read-only with respect to server config.
"""
import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime

sys.path.insert(0, r"D:\ForensicsAgent\bench")
import run_baseline as rb  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=10.0)
    ap.add_argument("--target", type=int, default=11781)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--out-prefix", required=True)
    args = ap.parse_args()

    key = rb.load_key()
    out_dir = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(out_dir, args.out_prefix + "_raw.jsonl")
    gpu_path = os.path.join(out_dir, args.out_prefix + "_gpu.csv")
    summary_path = os.path.join(out_dir, args.out_prefix + "_summary.json")

    glog = rb.GpuLogger(gpu_path)
    glog.start()
    time.sleep(2)

    deadline = time.time() + args.minutes * 60
    records = []
    prev_metrics = {}
    run = 0
    with open(raw_path, "w", encoding="utf-8") as f:
        while time.time() < deadline:
            if not rb.wait_idle(key, timeout=120):
                print("server busy; stop", flush=True)
                break
            nonce = f"sustained-{run}-{datetime.now().strftime('%H%M%S')}"
            text = rb.build_prompt(key, args.target, nonce, run % 1000)
            payload = rb.make_payload(text, args.max_tokens)
            t0 = time.perf_counter()
            try:
                r = rb.api("/v1/chat/completions", key, payload, timeout=600)
            except Exception as e:
                print("ERROR", repr(e), flush=True)
                break
            wall = time.perf_counter() - t0
            usage = r.get("usage", {})
            tim = r.get("timings", {})
            metrics_txt = rb.get_metrics_text(key)
            metrics = {k: rb.metric_value(metrics_txt, "llamacpp:" + k) for k in (
                "prompt_tokens_total", "tokens_predicted_total",
                "spec_decode_num_draft_tokens_total", "spec_decode_num_accepted_tokens_total",
                "spec_decode_num_drafts_total", "requests_processing")}
            delta = {}
            for k, v in metrics.items():
                if v is None:
                    delta[k] = None
                elif k in prev_metrics and prev_metrics[k] is not None:
                    delta[k] = v - prev_metrics[k]
                else:
                    delta[k] = v
            prev_metrics = metrics
            rec = {
                "run": run,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "cache_n": tim.get("cache_n"),
                "prompt_ms": tim.get("prompt_ms"),
                "prompt_tps": tim.get("prompt_per_second"),
                "decode_tps": tim.get("predicted_per_second"),
                "ttft_est_s": (tim.get("prompt_ms", 0) + tim.get("predicted_per_token_ms", 0)) / 1000.0,
                "draft_n": tim.get("draft_n"),
                "draft_n_accepted": tim.get("draft_n_accepted"),
                "wall_s": round(wall, 3),
                "finish_reason": r.get("choices", [{}])[0].get("finish_reason"),
                "delta": delta,
                "gpu_process_memory": rb.gpu_process_memory(),
            }
            rec["acceptance"] = (rec["draft_n_accepted"] / rec["draft_n"]) if rec["draft_n"] else None
            records.append(rec)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(f"run {run}: prompt={rec['prompt_tokens']} gen={rec['completion_tokens']} "
                  f"decode={rec['decode_tps']:.2f} prompt_ms={rec['prompt_ms']:.0f} "
                  f"draft={rec['draft_n']} acc={rec['acceptance']}", flush=True)
            run += 1
            time.sleep(1)

    glog.stop()
    time.sleep(1)

    def vals(rs, key):
        return [r[key] for r in rs if r.get(key) is not None]

    def stat(rs, key):
        v = vals(rs, key)
        if not v:
            return None
        return {"mean": statistics.mean(v), "min": min(v), "max": max(v),
                "stdev": statistics.stdev(v) if len(v) > 1 else None}

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "minutes_requested": args.minutes,
        "runs": len(records),
        "target_tokens": args.target,
        "max_tokens": args.max_tokens,
        "all": {k: stat(records, k) for k in ("decode_tps", "prompt_ms", "ttft_est_s", "wall_s", "acceptance")},
        "first3": {k: stat(records[:3], k) for k in ("decode_tps", "prompt_ms", "ttft_est_s", "acceptance")},
        "last3": {k: stat(records[-3:], k) for k in ("decode_tps", "prompt_ms", "ttft_est_s", "acceptance")},
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n=== SUSTAINED SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("raw", raw_path, "gpu", gpu_path)


if __name__ == "__main__":
    main()
