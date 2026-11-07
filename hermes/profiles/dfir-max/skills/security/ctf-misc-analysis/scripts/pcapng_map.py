#!/usr/bin/env python3
"""pcapng block walker — structure summary + raw-offset -> frame mapping.

Usage:
  python pcapng_map.py capture.pcapng                 # block summary
  python pcapng_map.py capture.pcapng 0x16a0ac 1774876  # locate offsets

Why: a whole-file grep hit (e.g. attack-looking strings inside a capture) is
not protocol traffic until you know which FRAME carries the bytes. EPB blocks
list [data_start, data_start+caplen) windows; a matching window gives the
frame number (EPB ordinal == tshark frame.number when the capture has no
Simple Packet Blocks; sanity-check against a known frame).

Block layout (LE assumed; envelope = type@0, total length@4):
  SHB 0x0A0D0D0A (byte-order magic @8; 1A2B3C4D = LE), IDB 1, SPB 3, NRB 4, ISB 5, EPB 6
  EPB: iface@8, ts_hi@12, ts_lo@16, caplen@20, origlen@24, data@28
  SPB: origlen@8, data@12
Timestamp = 64-bit count ((hi<<32)|lo) in if_tsresol units (default 1e-6 s).
"""
import struct
import sys

NAMES = {0x0A0D0D0A: 'SHB', 1: 'IDB', 2: 'PB', 3: 'SPB', 4: 'NRB', 5: 'ISB', 6: 'EPB'}


def walk(path, targets=()):
    d = open(path, 'rb').read()
    if d[8:12] != b'\x4d\x3c\x2b\x1a':
        print('note: SHB byte-order magic %r != LE (4D3C2B1A); script assumes LE' % d[8:12])
    off, frame = 0, 0
    counts, hits = {}, {t: [] for t in targets}
    while off + 12 <= len(d):
        btype, blen = struct.unpack_from('<II', d, off)
        if blen < 12 or off + blen > len(d):
            print('!! invalid block at 0x%x: type=0x%x len=%d' % (off, btype, blen))
            break
        name = NAMES.get(btype, '0x%x' % btype)
        counts[name] = counts.get(name, 0) + 1
        if btype == 6:
            frame += 1
            caplen = struct.unpack_from('<I', d, off + 20)[0]
            ds, de = off + 28, off + 28 + caplen
            for t in targets:
                if ds <= t < de:
                    hits[t].append((frame, off, caplen))
        off += blen
    print('size=%d blocks=%s epb_frames=%d tail=%d' % (len(d), counts, frame, len(d) - off))
    for t in targets:
        if hits[t]:
            for frame, boff, caplen in hits[t]:
                print('offset 0x%x -> frame %d (EPB@0x%x, caplen=%d)' % (t, frame, boff, caplen))
        else:
            print('offset 0x%x -> no frame (outside all EPB data windows)' % t)
    return counts, hits


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    walk(sys.argv[1], [int(x, 0) for x in sys.argv[2:]])
