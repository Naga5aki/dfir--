#!/usr/bin/env python3
"""视频抽帧：按固定间隔导出图片，供 OCR / 扫码使用。只读源文件。"""
import sys, json
from pathlib import Path

import cv2


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "用法: video_frames.py <视频> <输出目录> [间隔秒=10] [最多帧=30]"}, ensure_ascii=False))
        return 2
    src = Path(sys.argv[1])
    outdir = Path(sys.argv[2])
    step = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    maxf = int(sys.argv[4]) if len(sys.argv) > 4 else 30
    if not src.exists():
        print(json.dumps({"ok": False, "error": f"不存在: {src}"}, ensure_ascii=False))
        return 2
    outdir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        print(json.dumps({"ok": False, "error": "无法打开视频"}, ensure_ascii=False))
        return 1
    dur = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / (cap.get(cv2.CAP_PROP_FPS) or 25.0)
    written = []
    t = 0.0
    while t <= dur and len(written) < maxf:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        fp = outdir / f"frame_{int(t):05d}.png"
        cv2.imwrite(str(fp), frame)
        written.append(str(fp))
        t += step
    cap.release()
    print(json.dumps({"ok": True, "duration_sec": round(dur, 1), "count": len(written), "files": written},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
