#!/usr/bin/env python3
import struct, sys, re, zlib, os, json
from pathlib import Path

MAGIC_DEX = 0x0a786564
PAT = re.compile(rb'[A-Z0-9a-z\-/]{6,}')
TAGS = re.compile(rb'(?i)(aes|des|3des|cbc|cfb|ofb|ctr|gcm|chacha|blowfish|rc4|md5|sha|pkcs5|pkcs7|nopadding|pbkdf|hmac)', re.I)

def read_dex_strings(path: Path):
    data = path.read_bytes()
    if len(data) < 0x70:
        return []
    magic, = struct.unpack('<I', data[0:4])
    if magic != MAGIC_DEX:
        raise ValueError(f'bad dex magic: 0x{magic:08x}')
    string_ids_off, = struct.unpack('<I', data[0x3C:0x40])
    string_ids_size, = struct.unpack('<I', data[0x3E:0x42]) if False else struct.unpack('<I', data[0x40:0x44])
    strings = []
    for i in range(string_ids_size):
        off = string_ids_off + i * 4
        if off + 4 > len(data):
            break
        str_off, = struct.unpack('<I', data[off:off+4])
        if str_off >= len(data):
            continue
        s = bytearray()
        p = str_off
        while p < len(data) and data[p] != 0:
            s.append(data[p]); p += 1
        try:
            strings.append(s.decode('utf-8', errors='strict'))
        except Exception:
            pass
    return strings

root = Path(sys.argv[1]).parent
from zipfile import ZipFile
if Path(sys.argv[1]).suffix.lower() == '.apk':
    extract = root / 'dex_out'
    extract.mkdir(exist_ok=True)
    with ZipFile(sys.argv[1]) as z:
        for name in z.namelist():
            if name.startswith('classes') and name.endswith('.dex'):
                z.extract(name, extract)
    targets = list(extract.glob('classes*.dex'))
else:
    targets = [Path(p) for p in sys.argv[1:]]

hits = []
for t in targets:
    ss = read_dex_strings(t)
    for s in ss:
        if TAGS.search(s.encode('utf-8', errors='ignore')) and len(s) < 64:
            hits.append(str(s))
print(json.dumps(sorted(set(hits)), ensure_ascii=False, indent=2))
