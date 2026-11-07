#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""crc32_invert.py — CRC32 已知值反解 ≤4 字节明文（GF(2) 线性代数，唯一解）

原理：对固定长度，CRC32 是明文比特的仿射映射；明文 ≤4 字节（32 位空间）时为双射，
可从目标 CRC 直接解出唯一预像（高斯-约当消元），无需枚举；1–3 字节为单射（唯一解）。
>4 字节不可唯一反解（本工具拒绝）。长度必须取自载体声明字段（如 ZIP 条目 usize）。

用法:
  python crc32_invert.py --selftest [--count 1000]
  python crc32_invert.py --crc 0x12345678 [--crc 0x...] --length 4 [--format ascii|hex|raw] [-o out.bin]

  --format ascii : 打印可打印表示（默认）
  --format hex   : 打印十六进制
  --format raw   : 结果拼接写入 -o 文件（或 stdout hex）
回验：每个结果重算 crc32 断言相等；命中后仍应做结构与语义校验（解压/可读性）；
仅 CRC 相等不足以定论（用错长度会得到"碰撞预像"）。
"""
import argparse
import random
import struct
import sys
import zlib


def crc32_bits_of_plain(pbytes):
    """返回 (base_crc, cols)：明文各比特翻转对 CRC 的影响（GF(2) 列向量，8×len 列）"""
    base = zlib.crc32(pbytes) & 0xFFFFFFFF
    cols = []
    for bit in range(8 * len(pbytes)):
        q = bytearray(pbytes)
        q[bit // 8] ^= (1 << (bit % 8))
        cols.append(base ^ (zlib.crc32(bytes(q)) & 0xFFFFFFFF))
    return base, cols


def crc32_invert(target, length):
    """已知 target=crc32(P)，len(P)=length≤4，返回 P（bytes）或 None。
    必须给定正确长度；>4 字节拒绝。"""
    if length > 4 or length < 1:
        raise ValueError("length must be 1..4 (unique inverse); got %d" % length)
    base, cols = crc32_bits_of_plain(bytes(length))
    delta = base ^ (target & 0xFFFFFFFF)
    rows = []
    for i in range(32):
        row = 0
        for j, col in enumerate(cols):
            if (col >> i) & 1:
                row |= (1 << j)
        rows.append([row, (delta >> i) & 1])
    rank = 0
    piv = []
    for j in range(8 * length):
        sel = None
        for r in range(rank, len(rows)):
            if (rows[r][0] >> j) & 1:
                sel = r
                break
        if sel is None:
            continue
        rows[rank], rows[sel] = rows[sel], rows[rank]
        for r in range(len(rows)):
            if r != rank and ((rows[r][0] >> j) & 1):
                rows[r][0] ^= rows[rank][0]
                rows[r][1] ^= rows[rank][1]
        piv.append(j)
        rank += 1
    for r in range(rank, len(rows)):
        if rows[r][0] == 0 and rows[r][1] == 1:
            return None  # inconsistent (CRC 不属于该长度可解像集)
    sol = 0
    for idx, j in enumerate(piv):
        if rows[idx][1]:
            sol |= (1 << j)
    out = bytearray(length)
    for bit in range(8 * length):
        if (sol >> bit) & 1:
            out[bit // 8] ^= (1 << (bit % 8))
    out = bytes(out)
    if (zlib.crc32(out) & 0xFFFFFFFF) == (target & 0xFFFFFFFF):
        return out
    return None


def selftest(count):
    random.seed(7)
    bad = 0
    # 4 字节随机往返
    for _ in range(count):
        s = bytes(random.randrange(256) for _ in range(4))
        if crc32_invert(zlib.crc32(s) & 0xFFFFFFFF, 4) != s:
            bad += 1
    # 1–3 字节往返（单射）
    for ln in (1, 2, 3):
        for _ in range(max(8, count // 32)):
            s = bytes(random.randrange(256) for _ in range(ln))
            if crc32_invert(zlib.crc32(s) & 0xFFFFFFFF, ln) != s:
                bad += 1
    print("selftest: bad=%d / %d" % (bad, count + 3 * max(8, count // 32)))
    return 0 if bad == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="CRC32 ≤4-byte plaintext inverter (GF(2) solve)")
    ap.add_argument("--crc", action="append", default=[], help="target crc (hex or dec), repeatable")
    ap.add_argument("--length", type=int, help="plaintext length in bytes (1..4), required for solve")
    ap.add_argument("--format", choices=("ascii", "hex", "raw"), default="ascii")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--count", type=int, default=1000)
    a = ap.parse_args()

    if a.selftest:
        return selftest(a.count)
    if not a.crc or a.length is None:
        ap.error("--crc and --length are required unless --selftest")

    results = []
    for c in a.crc:
        target = int(c, 16) if c.lower().startswith("0x") else int(c, 0)
        if target > 0xFFFFFFFF:
            target &= 0xFFFFFFFF
        p = crc32_invert(target, a.length)
        if p is None:
            print("0x%08x -> UNSOLVABLE (inconsistent for length=%d)" % (target, a.length))
        else:
            results.append(p)
            if a.format == "ascii":
                print("0x%08x -> %s | ascii=%r" % (target, p.hex(), p.decode("latin1")))
            elif a.format == "hex":
                print("0x%08x -> %s" % (target, p.hex()))
    if a.format == "raw" and results:
        blob = b"".join(results)
        if a.output:
            open(a.output, "wb").write(blob)
            print("saved %d bytes -> %s" % (len(blob), a.output))
        else:
            print(blob.hex())
    return 0 if results or not a.crc else 2


if __name__ == "__main__":
    sys.exit(main())
