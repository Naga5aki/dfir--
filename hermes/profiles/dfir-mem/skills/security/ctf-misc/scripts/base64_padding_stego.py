#!/usr/bin/env python3
"""Extract data hidden in base64 padding bits (non-canonical encodings).

Usage: python base64_padding_stego.py <file-with-XX==-fragments>

Each input line is a 4-char base64 fragment (e.g. "UG=="). A fragment is
NON-CANONICAL when the 2nd character's alphabet index has low 4 bits != 0;
those 4 bits carry stego data (~6.25% random probability per fragment, so
nearly-all-non-canonical = stego). Extraction: idx(2nd char) & 0xF nibbles,
paired into bytes.

Validated on SecurityLab Misc bootcamp Day 2 trainer sample (2026-08-26):
46 fragments, 45 non-canonical, payload = flag{padding_bits_talk}.
"""
import base64
import sys

ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    frags = [ln.strip() for ln in open(sys.argv[1], encoding="utf-8") if ln.strip()]
    visible: list[str] = []
    nibbles: list[int] = []
    noncanon = 0
    for f in frags:
        try:
            visible.append(base64.b64decode(f).decode("latin1"))
        except Exception:
            visible.append(f"<bad:{f}>")
        if len(f) >= 2 and f[1] in ALPHA:
            low = ALPHA.index(f[1]) & 0xF
            nibbles.append(low)
            if low:
                noncanon += 1
    print("visible text:", "".join(visible))
    print(f"fragments={len(frags)} non_canonical={noncanon} "
          f"({100.0 * noncanon / max(len(frags), 1):.1f}%)")
    if len(nibbles) % 2:
        nibbles = nibbles[:-1]  # drop trailing odd nibble
    payload = bytes((nibbles[i] << 4) | nibbles[i + 1] for i in range(0, len(nibbles), 2))
    decoded = payload.decode(errors="replace")
    print("padding-bits payload:", repr(decoded))
    if "flag{" in decoded or "ctf{" in decoded.lower():
        print("FLAG-LIKE STRUCTURE FOUND")


if __name__ == "__main__":
    main()
