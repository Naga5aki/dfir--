#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bounded signature scanner: PNG/JPEG/ZIP/GZIP only.
Reports ALL candidate offsets per file; every hit must be manually verified
(header, trailer/directory, length, container end boundary, extracted hash).
Run from a directory of evidence copies:  python3 sigscan.py [file...]
"""
import sys, glob

SIGS = [
    ("PNG",  b"\x89PNG\r\n\x1a\n"),
    ("JPEG", b"\xff\xd8\xff"),
    ("ZIP",  b"PK\x03\x04"),
    ("ZIPE", b"PK\x05\x06"),
    ("GZIP", b"\x1f\x8b\x08"),
]

targets = sys.argv[1:] or sorted(glob.glob("sample*"))
for path in targets:
    data = open(path, "rb").read()
    hits = []
    for name, sig in SIGS:
        start = 0
        while True:
            i = data.find(sig, start)
            if i < 0:
                break
            hits.append((i, name))
            start = i + 1
    hits.sort()
    print(f"{path} ({len(data)} B):")
    if not hits:
        print("  (no PNG/JPEG/ZIP/GZIP signatures)")
    for off, name in hits:
        print(f"  +0x{off:06X} ({off}): {name}")
