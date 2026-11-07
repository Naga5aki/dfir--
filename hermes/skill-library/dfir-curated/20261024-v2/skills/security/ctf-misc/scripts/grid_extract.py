#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""grid_extract.py — 参数化等距/周期性像素网格提取器（纯标准库，无第三方依赖）

用途：CTF Misc 图像隐写"等距网格族"——按固定起点/步长/块尺寸采样载体像素，拼出
隐藏小图（文字提示/子图）。支持 PNG（颜色类型 0/2/4/6，过滤器 0-4）。

用法:
  python grid_extract.py -i carrier.png -p X,Y [-n DX,DY] [-b SX,SY] [-e X2,Y2]
                         [-o out.png] [--upscale K] [--rgb-dump out.bin] [--quiet]

  -i  载体 PNG（必填）
  -p  起点（必填）            例: -p 5,5
  -n  步长（默认 1,1）        例: -n 10,10
  -b  块尺寸（默认 1,1）      例: -b 1,1
  -e  终点坐标（默认按"步长对齐且块不越界"自动推导）
  -o  输出 PNG（默认 grid_extract_out.png）；--upscale K 另存 *_xK.png 放大版
  --rgb-dump  把提取的原始 RGB 字节写入文件（供逐字节比对/复算）

判定纪律：错误步长应无法恢复内容（负控制，字节一致率应≈随机）；产物先过后处理
（亮度阈值二值化 + 去抖动放大）再逐字符判读；工具路径与自写路径输出须一致。
可导入使用：read_png / write_png_rgb / grid_extract / default_end。
"""
import argparse
import struct
import sys
import zlib


def read_png(path):
    d = open(path, "rb").read()
    assert d[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos = 8
    w = h = None
    ct = None
    bitdepth = None
    idat = b""
    while pos < len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        typ = d[pos + 4:pos + 8]
        data = d[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, bitdepth, ct = struct.unpack(">IIBB", data[:10])
        elif typ == b"IDAT":
            idat += data
        elif typ == b"IEND":
            break
        pos += 12 + ln
    if bitdepth != 8 or ct not in (0, 2, 4, 6):
        raise ValueError("unsupported PNG (bitdepth=%s ct=%s); only 8-bit gray/RGB/GA/RGBA" % (bitdepth, ct))
    raw = zlib.decompress(idat)
    nch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    stride = w * nch
    out = bytearray()
    prev = bytearray(stride)
    pos = 0
    for _y in range(h):
        ft = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if ft == 1:
            for i in range(nch, stride):
                line[i] = (line[i] + line[i - nch]) & 255
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif ft == 3:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                b = prev[i]
                c = prev[i - nch] if i >= nch else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out += line
        prev = line
    return w, h, nch, bytes(out)


def write_png_rgb(path, w, h, rgb, level=9):
    def chunk(typ, payload):
        return struct.pack(">I", len(payload)) + typ + payload + \
               struct.pack(">I", zlib.crc32(typ + payload) & 0xffffffff)
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), level)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


def default_end(start, step, size, limit):
    """最后一个采样起点：步长对齐且块不越界（limit = 图像宽或高）"""
    if start + size > limit or start >= limit:
        return start
    k = (limit - size - start) // step
    return start + k * step


def grid_extract(px, W, H, nch, x1, y1, x2, y2, dx, dy, sx, sy):
    """按 (x1,y1)..(x2,y2) 以 dx×dy 为间隔，取 sx×sy 小块，行优先拼成新图（RGB）"""
    xs = list(range(x1, x2 + 1, dx))
    ys = list(range(y1, y2 + 1, dy))
    c = len(xs) * sx
    r = len(ys) * sy
    out = bytearray(r * c * 3)
    o = 0
    for y in ys:
        for yy in range(sy):
            row = []
            for x in xs:
                for xx in range(sx):
                    s = ((y + yy) * W + (x + xx)) * nch
                    row.append(px[s])
                    row.append(px[s + 1] if nch >= 3 else px[s])
                    row.append(px[s + 2] if nch >= 3 else px[s])
            out[o:o + c * 3] = bytes(row)
            o += c * 3
    return c, r, bytes(out)


def upscale_png(path, w, h, rgb, k):
    up = bytearray(w * k * h * k * 3)
    for y in range(h * k):
        for x in range(w * k):
            s = ((y // k) * w + (x // k)) * 3
            t = (y * w * k + x) * 3
            up[t:t + 3] = rgb[s:s + 3]
    write_png_rgb(path, w * k, h * k, bytes(up))


def _pair(s):
    a, b = s.split(",")
    return int(a), int(b)


def main():
    ap = argparse.ArgumentParser(description="equidistant/sampled pixel-grid extractor")
    ap.add_argument("-i", "--input", required=True)
    ap.add_argument("-p", "--point", required=True, type=_pair, help="start X,Y")
    ap.add_argument("-n", "--step", type=_pair, default=(1, 1), help="step DX,DY")
    ap.add_argument("-b", "--block", type=_pair, default=(1, 1), help="block SX,SY")
    ap.add_argument("-e", "--end", type=_pair, default=None, help="end X2,Y2 (default: auto)")
    ap.add_argument("-o", "--output", default="grid_extract_out.png")
    ap.add_argument("--upscale", type=int, default=0)
    ap.add_argument("--rgb-dump", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    W, H, nch, px = read_png(a.input)
    dx, dy = a.step
    sx, sy = a.block
    x1, y1 = a.point
    if a.end:
        x2, y2 = a.end
    else:
        x2 = default_end(x1, dx, sx, W)
        y2 = default_end(y1, dy, sy, H)
    if not a.quiet:
        print("carrier: %dx%d nch=%d" % (W, H, nch))
        print("grid: start=(%d,%d) step=%dx%d block=%dx%d end=(%d,%d)" % (x1, y1, dx, dy, sx, sy, x2, y2))
    c, r, rgb = grid_extract(px, W, H, nch, x1, y1, x2, y2, dx, dy, sx, sy)
    if not a.quiet:
        print("extracted: %dx%d" % (c, r))
    write_png_rgb(a.output, c, r, rgb)
    if not a.quiet:
        print("saved:", a.output)
    if a.upscale:
        up = a.output.rsplit(".", 1)[0] + "_x%d.png" % a.upscale
        upscale_png(up, c, r, rgb, a.upscale)
        if not a.quiet:
            print("saved:", up)
    if a.rgb_dump:
        open(a.rgb_dump, "wb").write(rgb)
        if not a.quiet:
            print("rgb dump:", a.rgb_dump)
    return 0


if __name__ == "__main__":
    sys.exit(main())
