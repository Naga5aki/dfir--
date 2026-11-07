#!/usr/bin/env python3
"""Controlled single-request baseline for the local llama-server.

Read-only with respect to server configuration: it only sends API requests.
Writes raw JSONL + summary JSON + GPU telemetry CSV into the bench directory.

Usage:
  python -I run_baseline.py --out-prefix baseline_YYYYmmdd_HHMM
"""
import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime

BASE = "http://127.0.0.1:8095"
KEY_FILE = r"D:\llm\secrets\llama.key"

PARA_TEMPLATE = (
    "取证记录第{i:05d}条：样本编号 A{i:05d}，采集时间 2026-10-30T{hh:02d}:{mm:02d}:{ss:02d}+08:00，"
    "主机 LEGION-83RU，证据文件 evidence_{i:05d}.bin，SHA-256 前缀 {h1}，进程 PID {pid}，"
    "网络连接 10.20.{o1}.{o2}:443，分析字段包含时间线、哈希、进程行为与网络连接。"
    "复核时必须引用原始字段，不得省略上下文；结论与证据之间要逐项对应。"
)


def para(i):
    return PARA_TEMPLATE.format(
        i=i, hh=(i * 7) % 24, mm=(i * 13) % 60, ss=(i * 29) % 60,
        h1=hashlib.sha256(f"evidence-{i}".encode()).hexdigest()[:16],
        pid=3000 + (i * 37) % 60000,
        o1=(i * 11) % 256, o2=(i * 17) % 256,
    )


def load_key():
    with open(KEY_FILE, encoding="utf-8") as f:
        return f.read().strip()


def api(path, key, payload=None, timeout=900):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def metric(key, name):
    txt = api("/metrics", key, timeout=30)
    # /metrics is text/plain, not JSON; this function is unused for that reason.
    raise RuntimeError("unused")


def get_metrics_text(key):
    req = urllib.request.Request(BASE + "/metrics", headers={"Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def metric_value(text, name):
    for line in text.splitlines():
        if line.startswith(name + " "):
            return float(line.split()[1])
    return None


def wait_idle(key, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            txt = get_metrics_text(key)
            busy = metric_value(txt, "llamacpp:requests_processing")
            deferred = metric_value(txt, "llamacpp:requests_deferred")
            if busy == 0 and deferred == 0:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def token_count(key, text):
    r = api("/tokenize", key, {"content": text}, timeout=120)
    return len(r["tokens"])


def build_prompt(key, target_tokens, nonce, variant):
    """Build a synthetic Chinese evidence text near target_tokens (raw content).

    Granularity is one paragraph (~100-130 tokens), not a 16-paragraph block,
    so the loop converges instead of oscillating around the target.
    """
    if target_tokens <= 300:
        return (
            f"本次请求编号 {nonce}。\n"
            "请阅读下面的证据并回答：样本 A00001 的采集时间是什么？必须给出原始字段。\n"
            "证据：样本编号 A00001，采集时间 2026-10-30T08:15:30+08:00，主机 LEGION-83RU，"
            "证据文件 evidence_00001.bin，SHA-256 前缀 4f9c2a7d1e8b3065。"
        )
    base = 100000 * (variant % 1000) + 1
    unit_tokens = max(1, token_count(key, para(base)))
    n = max(1, round((target_tokens - 60) / unit_tokens))
    tail = (
        "\n\n请完成：基于以上材料，写出第 1 段、最后一段的时间线和证据编号，"
        "并给出三条可复核的定位。不要省略时间、哈希或进程字段。"
    )
    def compose(n_units):
        return (f"本次请求编号 {nonce}。\n"
                + "".join(para(base + j) for j in range(max(1, n_units)))
                + tail)
    text = compose(n)
    for _ in range(5):
        nt = token_count(key, text)
        tol = max(40, target_tokens // 100)
        if abs(nt - target_tokens) <= tol:
            break
        n = max(1, n + round((target_tokens - nt) / unit_tokens))
        text = compose(n)
    return text


class GpuLogger(threading.Thread):
    def __init__(self, path):
        super().__init__(daemon=True)
        self.path = path
        self.stop_flag = threading.Event()
        self.proc = None

    def run(self):
        cmd = ["nvidia-smi",
               "--query-gpu=timestamp,power.draw,clocks.sm,clocks.mem,temperature.gpu,memory.used,memory.total,utilization.gpu",
               "--format=csv,noheader,nounits", "-l", "1"]
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, bufsize=1)
            with open(self.path, "w", encoding="utf-8", newline="") as f:
                f.write("timestamp,power_w,sm_mhz,mem_mhz,temp_c,mem_used_mib,mem_total_mib,gpu_util_pct\n")
                for line in self.proc.stdout:
                    if self.stop_flag.is_set():
                        break
                    line = line.strip()
                    if line:
                        f.write(line + "\n")
                        f.flush()
        except Exception as e:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(f"# logger error: {e}\n")

    def stop(self):
        self.stop_flag.set()
        if self.proc:
            try:
                self.proc.terminate()
            except Exception:
                pass


def gpu_process_memory():
    ps = (
        "$p = Get-Process llama-server -ErrorAction SilentlyContinue | Select-Object -First 1; "
        "if ($p) { $serverPid = $p.Id; "
        "$c = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory "
        "| Where-Object { $_.Name -like ('pid_' + $serverPid + '_*') } | Select-Object -First 1; "
        "if ($c) { Write-Output (\"{0},{1},{2}\" -f $serverPid,$c.DedicatedUsage,$c.SharedUsage) } }"
    )
    try:
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps],
                                      text=True, timeout=30).strip()
        if "," in out:
            a, b, c = out.split(",")
            return {"pid": int(a), "dedicated_bytes": int(b), "shared_bytes": int(c)}
    except Exception as e:
        return {"error": str(e)}
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--targets", default="short:120,12k:11781,32k:32000,56k:55500")
    ap.add_argument("--skip-warmup", action="store_true")
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    key = load_key()
    out_dir = os.path.dirname(os.path.abspath(__file__))
    prefix = os.path.join(out_dir, args.out_prefix)
    gpu_path = prefix + "_gpu.csv"
    raw_path = prefix + "_raw.jsonl"
    summary_path = prefix + "_summary.json"

    targets = []
    for part in args.targets.split(","):
        name, n = part.split(":")
        targets.append((name, int(n)))

    glog = GpuLogger(gpu_path)
    glog.start()
    time.sleep(2)

    records = []
    raw = open(raw_path, "w", encoding="utf-8")
    try:
        if not args.skip_warmup:
            if not wait_idle(key):
                raise SystemExit("server busy before warmup")
            warm = build_prompt(key, 120, "warmup-" + datetime.now().strftime("%H%M%S"), 0)
            payload = make_payload(warm, args.max_tokens)
            t0 = time.perf_counter()
            r = api("/v1/chat/completions", key, payload, timeout=300)
            wall = time.perf_counter() - t0
            print(f"warmup: prompt={r['usage']['prompt_tokens']} gen={r['usage']['completion_tokens']} "
                  f"decode={r['timings']['predicted_per_second']:.2f} t/s wall={wall:.1f}s", flush=True)
            time.sleep(3)

        for name, target in targets:
            for run in range(1, args.runs + 1):
                if not wait_idle(key, timeout=120):
                    print(f"SKIP {name} run {run}: server busy", flush=True)
                    continue
                nonce = f"{name}-{run}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                text = build_prompt(key, target, nonce, run)
                raw_prompt_tokens = token_count(key, text)
                payload = make_payload(text, args.max_tokens)
                m_before = get_metrics_text(key)
                t0 = time.perf_counter()
                err = None
                r = None
                try:
                    r = api("/v1/chat/completions", key, payload, timeout=900)
                except Exception as e:
                    err = repr(e)
                wall = time.perf_counter() - t0
                m_after = get_metrics_text(key)
                if r is None:
                    rec = {"label": name, "target_tokens": target, "run": run,
                           "prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
                           "raw_content_tokens": raw_prompt_tokens, "wall_s": round(wall, 3),
                           "error": err}
                    records.append(rec)
                    raw.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    raw.flush()
                    print(f"{name} run{run}: ERROR {err}", flush=True)
                    continue
                usage = r.get("usage", {})
                tim = r.get("timings", {})
                rec = {
                    "label": name, "target_tokens": target, "run": run,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "prompt_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "prompt_chars": len(text),
                    "raw_content_tokens": raw_prompt_tokens,
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                    "cache_n": tim.get("cache_n"),
                    "prompt_ms": tim.get("prompt_ms"),
                    "prompt_tps": tim.get("prompt_per_second"),
                    "predicted_ms": tim.get("predicted_ms"),
                    "decode_tps": tim.get("predicted_per_second"),
                    "ttft_est_s": (tim.get("prompt_ms", 0) + tim.get("predicted_per_token_ms", 0)) / 1000.0,
                    "wall_s": round(wall, 3),
                    "finish_reason": r.get("choices", [{}])[0].get("finish_reason"),
                    "content_chars": len((r.get("choices", [{}])[0].get("message", {}) or {}).get("content") or ""),
                    "reasoning_chars": len((r.get("choices", [{}])[0].get("message", {}) or {}).get("reasoning_content") or ""),
                    "metrics": {
                        "prompt_tokens_total": metric_value(m_after, "llamacpp:prompt_tokens_total"),
                        "predicted_total": metric_value(m_after, "llamacpp:tokens_predicted_total"),
                        "requests_processing": metric_value(m_after, "llamacpp:requests_processing"),
                        "spec_draft": metric_value(m_after, "llamacpp:spec_decode_num_draft_tokens_total"),
                        "spec_accepted": metric_value(m_after, "llamacpp:spec_decode_num_accepted_tokens_total"),
                        "spec_drafts": metric_value(m_after, "llamacpp:spec_decode_num_drafts_total"),
                    },
                    "gpu_process_memory": gpu_process_memory(),
                }
                records.append(rec)
                raw.write(json.dumps(rec, ensure_ascii=False) + "\n")
                raw.flush()
                print(f"{name} run{run}: prompt={rec['prompt_tokens']} gen={rec['completion_tokens']} "
                      f"cache_n={rec['cache_n']} prefill={rec['prompt_tps']:.1f} t/s "
                      f"decode={rec['decode_tps']:.2f} t/s ttft~{rec['ttft_est_s']:.2f}s "
                      f"wall={rec['wall_s']:.1f}s finish={rec['finish_reason']}", flush=True)
                time.sleep(2)
    finally:
        raw.close()
        glog.stop()
        time.sleep(1)

    # Summary by label
    summary = {"generated_at": datetime.now().isoformat(timespec="seconds"),
               "config": "64K, ngl64, q8/q8, no MTP, reasoning budget 2048",
               "max_tokens": args.max_tokens, "runs_requested": args.runs,
               "conditions": {}}
    for name, target in targets:
        rs = [r for r in records if r["label"] == name and "error" not in r]
        if not rs:
            summary["conditions"][name] = {"target_tokens": target, "n": 0}
            continue
        def vals(k):
            return [r[k] for r in rs if r.get(k) is not None]
        summary["conditions"][name] = {
            "target_tokens": target,
            "n": len(rs),
            "prompt_tokens": vals("prompt_tokens"),
            "completion_tokens": vals("completion_tokens"),
            "cache_n": vals("cache_n"),
            "prompt_tps": vals("prompt_tps"),
            "decode_tps": vals("decode_tps"),
            "ttft_est_s": vals("ttft_est_s"),
            "wall_s": vals("wall_s"),
            "decode_mean": statistics.mean(vals("decode_tps")) if vals("decode_tps") else None,
            "decode_min": min(vals("decode_tps")) if vals("decode_tps") else None,
            "decode_max": max(vals("decode_tps")) if vals("decode_tps") else None,
            "decode_stdev": statistics.stdev(vals("decode_tps")) if len(vals("decode_tps")) > 1 else None,
            "prompt_tps_mean": statistics.mean(vals("prompt_tps")) if vals("prompt_tps") else None,
            "ttft_mean": statistics.mean(vals("ttft_est_s")) if vals("ttft_est_s") else None,
        }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n=== SUMMARY ===")
    print(json.dumps(summary["conditions"], ensure_ascii=False, indent=2))
    print(f"\nraw: {raw_path}\nsummary: {summary_path}\ngpu: {gpu_path}")


def make_payload(text, max_tokens):
    return {
        "messages": [{"role": "user", "content": text}],
        "max_tokens": max_tokens,
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.05,
        "seed": 42,
        "cache_prompt": False,
        "stream": False,
        "ignore_eos": True,
        "timings_per_token": False,
        "chat_template_kwargs": {"enable_thinking": True},
    }


if __name__ == "__main__":
    main()
