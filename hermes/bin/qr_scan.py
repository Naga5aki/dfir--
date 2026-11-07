#!/usr/bin/env python3
"""视频/图片二维码提取：按采样抽帧 -> cv2.QRCodeDetector 解码。只读源文件，不写检材。"""
import sys, json
from pathlib import Path

import cv2


def scan_image(img, detector):
    out = []
    ok, decoded, points, _ = detector.detectAndDecodeMulti(img)
    if ok:
        for d in decoded:
            if d:
                out.append(d)
    else:
        d, _, _ = detector.detectAndDecode(img)
        if d:
            out.append(d)
    return out


def scan_video(path: Path, step_sec: float, max_frames: int):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"ok": False, "error": "无法打开视频"}
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    dur = total / fps if fps else 0
    step = max(1, int(round(fps * step_sec)))
    detector = cv2.QRCodeDetector()
    found = {}
    idx = 0
    taken = 0
    t = 0.0
    while taken < max_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            break
        for text in scan_image(frame, detector):
            found.setdefault(text, round(idx / fps, 2))
        idx += step
        taken += 1
        t = idx / fps
        if total and idx >= total:
            break
    cap.release()
    return {"ok": True, "fps": round(fps, 2), "duration_sec": round(dur, 1),
            "frames_scanned": taken, "qr": [{"text": k, "at_sec": v} for k, v in found.items()]}


def scan_still(path: Path):
    detector = cv2.QRCodeDetector()
    img = cv2.imread(str(path))
    if img is None:
        return {"ok": False, "error": "无法读取图片"}
    return {"ok": True, "qr": [{"text": t, "at_sec": None} for t in scan_image(img, detector)]}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "用法: qr_scan.py <视频|图片> [步长秒=0.5] [最多帧=200]"}, ensure_ascii=False))
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(json.dumps({"ok": False, "error": f"文件不存在: {p}"}, ensure_ascii=False))
        return 2
    IMG = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")
    if p.suffix.lower() in IMG:
        res = scan_still(p)
    else:
        step = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
        maxf = int(sys.argv[3]) if len(sys.argv) > 3 else 200
        res = scan_video(p, step, maxf)
        # 解密后的素材常是 .tmp 后缀，按视频打不开时退回按图片试
        if not res.get("ok"):
            res = scan_still(p)
    res["file"] = str(p)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
