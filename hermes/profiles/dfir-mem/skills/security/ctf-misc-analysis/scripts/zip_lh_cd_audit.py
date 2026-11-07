#!/usr/bin/env python3
"""zip_lh_cd_audit.py — ZIP local-header vs central-directory auditor.

Detects fake encryption (GP-flag bit0 set in CD but clear in LH, or vice versa),
size/CRC mismatches between LH and CD, trailing bytes after the EOCD, and nested
ZIP signatures that make blind signature-patching dangerous. Optional --fix
clears bit0 ONLY in the outer archive's own CD entries (delimited by its EOCD),
never touching nested stored archives.

Usage:
  python3 zip_lh_cd_audit.py <file.zip>            # audit only
  python3 zip_lh_cd_audit.py <file.zip> --fix out.zip
"""
import struct, sys, re

def find_eocd(raw):
    p = raw.rfind(b'PK\x05\x06')
    if p < 0:
        sys.exit("no EOCD found — not a ZIP or truncated")
    nent, cdsize, cdoff = struct.unpack_from('<HII', raw, p+10)
    return p, nent, cdsize, cdoff

def read_lh(raw, off):
    if raw[off:off+4] != b'PK\x03\x04':
        return None
    ver, flags, method = struct.unpack_from('<HHH', raw, off+4)
    crc, csize, usize = struct.unpack_from('<III', raw, off+14)
    nlen, elen = struct.unpack_from('<HH', raw, off+26)
    name = raw[off+30:off+30+nlen].decode('latin1')
    return dict(flags=flags, method=method, crc=crc, csize=csize, usize=usize, name=name)

def main():
    path = sys.argv[1]
    fix_out = None
    if len(sys.argv) > 3 and sys.argv[2] == '--fix':
        fix_out = sys.argv[3]
    raw = open(path, 'rb').read()
    eocd, nent, cdsize, cdoff = find_eocd(raw)
    zip_end = eocd + 22
    print(f"file: {path} ({len(raw)} bytes)")
    print(f"EOCD @{eocd}: entries={nent} CD @{cdoff}..{cdoff+cdsize} zip-end={zip_end}")

    anomalies = []
    entries = []
    p = cdoff
    for _ in range(nent):
        if raw[p:p+4] != b'PK\x01\x02':
            anomalies.append(f"bad CD signature @{p}")
            break
        vmade, vneed, cdflags, cdmethod = struct.unpack_from('<HHHH', raw, p+4)
        cdcrc, cdcsize, cdusize = struct.unpack_from('<III', raw, p+16)
        nlen, elen, clen = struct.unpack_from('<HHH', raw, p+28)
        name = raw[p+46:p+46+nlen].decode('latin1')
        lho = struct.unpack_from('<I', raw, p+42)[0]
        lh = read_lh(raw, lho)
        print(f"  {name}: CD(flags=0x{cdflags:04x},method={cdmethod},crc=0x{cdcrc:08x},"
              f"csize={cdcsize},usize={cdusize}) LH@{lho} "
              f"LH(flags=0x{lh['flags']:04x},method={lh['method']},crc=0x{lh['crc']:08x},"
              f"csize={lh['csize']},usize={lh['usize']})" if lh else
              f"  {name}: CD(flags=0x{cdflags:04x}) LH@{lho} MISSING")
        if lh:
            if (cdflags & 1) and not (lh['flags'] & 1):
                anomalies.append(f"FAKE ENCRYPTION: {name} — CD bit0=1 (encrypted) but LH bit0=0 (plaintext)")
            if (lh['flags'] & 1) and not (cdflags & 1):
                anomalies.append(f"REVERSE FAKE: {name} — LH bit0=1 but CD bit0=0 (data IS encrypted; some tools will extract garbage)")
            for field in ('crc', 'csize', 'usize', 'method'):
                if lh[field] != dict(crc=cdcrc, csize=cdcsize, usize=cdusize, method=cdmethod)[field]:
                    anomalies.append(f"FIELD MISMATCH: {name} {field}: LH={lh[field]} CD={dict(crc=cdcrc, csize=cdcsize, usize=cdusize, method=cdmethod)[field]}")
        entries.append((p, name))
        p += 46 + nlen + elen + clen

    # trailing bytes after EOCD
    if len(raw) > zip_end:
        trail = raw[zip_end:]
        nz = sum(1 for b in trail if b != 0)
        print(f"TRAILING: {len(trail)} bytes after EOCD ({nz} non-zero)")
        # UTF-16LE ASCII detection
        m = re.search(rb'(?:[\x20-\x7e]\x00){3,}', trail)
        if m:
            print(f"  UTF-16LE text in trailing: {m.group().decode('utf-16le')!r}")
        print(f"  head: {trail[:32].hex()}")

    # nested ZIP signatures outside the CD/LH regions — warn against blind patching
    cd_span = set()
    q = cdoff
    for _ in range(nent):
        if raw[q:q+4] != b'PK\x01\x02':
            break
        nlen, elen, clen = struct.unpack_from('<HHH', raw, q+28)
        cd_span.update(range(q, q+46+nlen+elen+clen))
        q += 46 + nlen + elen + clen
    nested = [m.start() for m in re.finditer(re.escape(b'PK\x01\x02'), raw)
              if m.start() not in cd_span]
    if nested:
        print(f"NESTED ZIP CD signatures outside outer CD ({len(nested)} @ {nested[:6]}): "
              f"blind signature-scan patching WILL corrupt a nested stored zip — fix only within "
              f"EOCD-delimited CD range (as this script does).")

    if anomalies:
        print("\n== ANOMALIES ==")
        for a in anomalies:
            print(" -", a)
    else:
        print("\nno LH/CD anomalies")

    if fix_out:
        fixed = bytearray(raw)
        patched = 0
        for pp, name in entries:
            flags = struct.unpack_from('<H', fixed, pp+8)[0]
            if flags & 1:
                lh = read_lh(raw, struct.unpack_from('<I', raw, pp+42)[0])
                if lh and not (lh['flags'] & 1):
                    struct.pack_into('<H', fixed, pp+8, flags & ~1)
                    patched += 1
                    print(f"patched CD@{pp} ({name}): flags 0x{flags:04x} -> 0x{flags & ~1:04x}")
        open(fix_out, 'wb').write(bytes(fixed))
        print(f"wrote {fix_out} ({patched} entries patched)")

if __name__ == '__main__':
    main()
