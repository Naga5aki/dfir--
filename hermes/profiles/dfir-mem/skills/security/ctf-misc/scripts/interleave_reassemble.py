#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""interleave_reassemble.py — 无索引交错分片重组（RAID0 式逐 strip 轮询）

场景：N 个同源分片、无内嵌索引、无声明卷序；数据按 strip 大小在各分片间轮询分布
（全局块 gi 属于分片 gi%N 的局部块 gi//N）。余数分片（长度差 1 块）属正常。

用法:
  python interleave_reassemble.py -o out.bin [--strip N] [--order i,j,k,...]
                                  [--check-zip] [--check-magic HEX] part1 part2 ...

  part1..N  按"位置顺序"给出；或先按自然顺序给出再用 --order 置换：
            --order 3,4,5,1,0,2 表示"给出的第 3、4、5、1、0、2 个文件"依次位于位置 0..5。
  --check-zip    重组后用 zipfile 全检（失败退出码 3；负控制：错误 strip/顺序必须使其损坏）
  --check-magic  断言输出以给定 hex 前缀开头（如 504b0304）
  --first-block  打印输出首尾哨兵 hex（便于结构对照）

纪律：顺序与条宽必须由结构自检裁定（产物过目标容器解析），不得靠文件名或直觉；
错误条宽/顺序必须能损坏解析——这是回归与负控制的判据。
可导入使用：reassemble(parts, strip) -> bytes。
"""
import argparse
import io
import sys
import zipfile


def reassemble(parts, strip):
    """RAID0 式重组：全局块 gi -> 分片 gi%N 的局部块 gi//N（strip 字节/块）。"""
    n = len(parts)
    if n == 0:
        return b""
    nb = [(len(d) + strip - 1) // strip for d in parts]
    out = bytearray()
    for gi in range(n * max(nb)):
        k = gi % n
        b = gi // n
        if b < nb[k]:
            off = b * strip
            out += parts[k][off:off + strip]
    return bytes(out)


def main():
    ap = argparse.ArgumentParser(description="index-less interleaved shard reassembly")
    ap.add_argument("parts", nargs="+")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--strip", type=int, default=1)
    ap.add_argument("--order", default=None, help="comma list of indices applying to the given parts")
    ap.add_argument("--check-zip", action="store_true")
    ap.add_argument("--check-magic", default=None, help="hex prefix assertion")
    ap.add_argument("--first-block", action="store_true")
    a = ap.parse_args()

    data = [open(p, "rb").read() for p in a.parts]
    if a.order is not None:
        order = [int(x) for x in a.order.split(",")]
        if sorted(order) != list(range(len(data))):
            ap.error("--order must be a permutation of 0..%d" % (len(data) - 1))
        data = [data[i] for i in order]
    rec = reassemble(data, a.strip)
    open(a.output, "wb").write(rec)
    print("reassembled: %d bytes -> %s (strip=%d, parts=%d)" % (len(rec), a.output, a.strip, len(data)))

    if a.first_block:
        print("head16=%s tail8=%s" % (rec[:16].hex(), rec[-8:].hex()))
    if a.check_magic:
        ok = rec.startswith(bytes.fromhex(a.check_magic))
        print("magic check %s: %s" % (a.check_magic, "PASS" if ok else "FAIL"))
        if not ok:
            return 3
    if a.check_zip:
        try:
            zf = zipfile.ZipFile(io.BytesIO(rec))
            bad = zf.testzip()
            if bad is None:
                print("zip check: PASS (%d entries)" % len(zf.namelist()))
            else:
                print("zip check: FAIL (bad entry: %s)" % bad)
                return 3
        except Exception as e:
            print("zip check: FAIL (%r)" % e)
            return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
