#!/usr/bin/env python
"""iOS backup probes. Read-only. Prints district names or an image trailer.

  python ios_backup_probe.py districts <Photos.sqlite>
  python ios_backup_probe.py trailer <image>

District names live in ZADDITIONALASSETATTRIBUTES.ZREVERSELOCATIONDATA
(a keyed archive). ZASSET.ZLOCATIONDATA is a coordinate blob, not a district.
"""

import plistlib
import sqlite3
import sys
from collections import Counter
from pathlib import Path


def fail(msg: str) -> None:
    print(msg)
    sys.exit(1)


def walk(obj, acc):
    if isinstance(obj, str):
        acc.append(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            walk(value, acc)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            walk(value, acc)


def districts(path: str) -> None:
    db = Path(path)
    if not db.is_file():
        fail(f"not a file: {db}")
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    rows = con.execute(
        """
        SELECT z.ZLATITUDE, z.ZLONGITUDE, a.ZREVERSELOCATIONDATA
        FROM ZADDITIONALASSETATTRIBUTES a
        JOIN ZASSET z ON z.ZADDITIONALATTRIBUTES = a.Z_PK
        WHERE a.ZREVERSELOCATIONDATA IS NOT NULL
        """
    ).fetchall()
    counts = Counter()
    shown = set()
    for lat, lon, blob in rows:
        try:
            obj = plistlib.loads(blob)
        except Exception:
            continue
        names = []
        walk(obj, names)
        districts_here = [n for n in names if n.endswith("区") or n.endswith("市")]
        for name in districts_here:
            counts[name] += 1
        key = (round(lat or 0, 3), round(lon or 0, 3), tuple(districts_here[:4]))
        if districts_here and key not in shown:
            shown.add(key)
            print(f"{lat:.3f},{lon:.3f}\t" + " | ".join(districts_here[:6]))
    print("COUNTS")
    for name, n in counts.most_common(30):
        print(f"{n}\t{name}")
    if not counts:
        fail("ZREVERSELOCATIONDATA parsed 0 district strings")


def trailer(path: str) -> None:
    data = Path(path).read_bytes()
    iend = data.find(b"IEND")
    print(f"size={len(data)} iend={iend}")
    if iend < 0:
        print("no IEND; not a PNG with a trailer")
        return
    # IEND chunk: 4 type bytes + 4 CRC, then any appended file.
    start = iend + 8
    head = data[start:start + 16]
    print("after_iend_hex", head.hex())
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        print("TRAILER OLE/CFB D0CF11E0")
        print(f"carve_offset {start}")
        print("do_not_ocr_png_surface")
    elif head.startswith(b"PK"):
        print("TRAILER ZIP")
        print(f"carve_offset {start}")
    else:
        print("no appended OLE/ZIP")


def sum_by_uuid(path: str, table: str, id_column: str, amount_column: str) -> None:
    for name in (table, id_column, amount_column):
        if not name.replace("_", "").isalnum():
            fail(f"unsafe identifier: {name}")
    db = Path(path)
    if not db.is_file():
        fail(f"not a file: {db}")
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        rows = con.execute(
            f'SELECT "{id_column}", "{amount_column}" FROM "{table}" '
            f'WHERE "{id_column}" IS NOT NULL AND "{amount_column}" IS NOT NULL'
        ).fetchall()
    finally:
        con.close()
    seen = {}
    for row_id, amount in rows:
        seen.setdefault(str(row_id), int(amount))
    total = 0
    for row_id, amount in seen.items():
        print(f"{row_id}\t{amount}")
        total += amount
    print(f"SUM {total}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) == 6 and sys.argv[1] == "sum-by-uuid":
        sum_by_uuid(*sys.argv[2:])
        return
    if len(sys.argv) != 3 or sys.argv[1] not in ("districts", "trailer"):
        fail("usage: ios_backup_probe.py districts <Photos.sqlite> | trailer <image> | sum-by-uuid <sqlite> <table> <id-column> <amount-column>")
    if sys.argv[1] == "districts":
        districts(sys.argv[2])
    else:
        trailer(sys.argv[2])


if __name__ == "__main__":
    main()
