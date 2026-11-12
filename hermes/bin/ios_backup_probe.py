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


def apps(path: str) -> None:
    root = Path(path)
    containers = root / "private" / "var" / "mobile" / "Containers" / "Data" / "Application"
    if not containers.is_dir():
        fail(f"not an iOS backup root: {root}")
    names = sorted(d.name for d in containers.iterdir() if d.is_dir() and not d.name.startswith("com.apple."))
    print(f"THIRD_PARTY {len(names)}")
    for name in names:
        print(name)


def ledger(path: str, category: str = "", account: str = "") -> None:
    """Locate the bookkeeping database and, given a category, sum it by trade uuid.

    Amounts are stored in fen. Category rows are duplicated in this app, so the
    join is grouped by trade uuid before summing.
    """
    root = Path(path)
    containers = root / "private" / "var" / "mobile" / "Containers" / "Data" / "Application"
    if not containers.is_dir():
        fail(f"not an iOS backup root: {root}")
    keywords = ("jizhang", "account", "money", "ledger", "wallet", "bill", "bookkeep")
    db = None
    for container in containers.iterdir():
        if not container.is_dir() or not any(k in container.name.lower() for k in keywords):
            continue
        for found in container.rglob("*.db"):
            if found.name.startswith("observations"):
                continue
            db = found
            print(f"CONTAINER {container.name}")
            print(f"DB {db}")
            break
        if db:
            break
    if db is None:
        fail("no bookkeeping database; run `apps` and name the bundle")
    if not category:
        return
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        rows = con.execute(
            """
            SELECT t.uuid, t.money, IFNULL(a.name, '')
            FROM TBL_TRADE t
            JOIN TBL_OUTGOCATEGORYINFO c ON c.uuid = t.typeuuid
            LEFT JOIN TBL_ACCOUNTINFO a ON a.uuid = t.accountuuid
            WHERE t.isdelete = 0 AND c.name = ?
            GROUP BY t.uuid
            """,
            (category,),
        ).fetchall()
    finally:
        con.close()
    if account:
        rows = [r for r in rows if account in (r[2] or "")]
    total = sum(int(money) for _, money, _ in rows)
    for uuid, money, account_name in rows:
        print(f"{uuid}\t{money}\t{account_name}")
    print(f"FEN {total}")
    print(f"YUAN {total // 100}")


def notes(path: str, keyword: str) -> None:
    """Print third-party note rows whose title or content contains the keyword."""
    root = Path(path)
    containers = root / "private" / "var" / "mobile" / "Containers" / "Data" / "Application"
    if not containers.is_dir():
        fail(f"not an iOS backup root: {root}")
    found = 0
    for db in containers.rglob("*.sqlite"):
        try:
            con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
            tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            if "Note" not in tables:
                con.close()
                continue
            rows = con.execute("SELECT title, content FROM Note WHERE title LIKE ? OR content LIKE ?",
                               (f"%{keyword}%", f"%{keyword}%")).fetchall()
            con.close()
        except sqlite3.DatabaseError:
            continue
        for title, content in rows:
            found += 1
            print(f"DB {db}")
            print(f"NOTE {title} | {content}")
    if not found:
        fail(f"no note contains {keyword!r}")


def docprice(root: str, conversation_hash: str, keyword: str) -> None:
    """One-shot: chat image → password from the same chat → decrypted price row.

    The WeChat container layout (Documents/<id>/Img/<conv>/*.pic, DB/message_3.sqlite,
    Chat_<conv>) is the iOS WeChat structure, not a case-specific path.
    """
    import io
    import re
    import zipfile
    import msoffcrypto

    image = find_chat_image(root, conversation_hash)
    if image is None:
        fail(f"no image with an OLE trailer in conversation {conversation_hash}")
    print(f"IMAGE {image}")
    wx_docs = image.parents[2]
    db = wx_docs / "DB" / "message_3.sqlite"
    if not db.is_file():
        fail(f"chat database not found under {wx_docs}")
    password = chat_password(str(db), f"Chat_{conversation_hash}")
    print(f"PASSWORD {password}")
    data = image.read_bytes()
    start = data.find(b"\xd0\xcf\x11\xe0")
    office = msoffcrypto.OfficeFile(io.BytesIO(data[start:]))
    office.load_key(password=password)
    out = io.BytesIO()
    office.decrypt(out)
    book = zipfile.ZipFile(io.BytesIO(out.getvalue()))
    strings = re.findall(r"<t[^>]*>([^<]*)</t>", book.read("xl/sharedStrings.xml").decode("utf-8"))
    sheet = book.read("xl/worksheets/sheet1.xml").decode("utf-8")
    target = next((i for i, s in enumerate(strings) if keyword in s), None)
    if target is None:
        fail(f"no shared string contains {keyword!r}; strings={strings[:20]}")
    for row in re.findall(r"<row.*?</row>", sheet):
        cells = re.findall(r'<c [^>]*t="s"[^>]*><v>(\d+)</v>', row)
        if not cells or int(cells[0]) != target:
            continue
        value = re.findall(r"<c [^>]*><v>([^<]*)</v>", row)
        print(f"ROW {strings[target]}")
        print(f"PRICE {value[-1]}")
        return
    fail(f"no row for {keyword!r}")


def device(path: str) -> None:
    """Print device identity fields from Platform/DeviceInfo (plist or xml)."""
    import plistlib

    info = Path(path) / "Platform" / "DeviceInfo"
    data = None
    source = None
    for name in ("Manifest.plist", "Manifest.xml"):
        candidate = info / name
        if candidate.is_file():
            raw = candidate.read_bytes()
            if raw[:8] == b"bplist00":
                data = plistlib.loads(raw)
            else:
                data = plistlib.loads(raw)
            source = candidate
            break
    if data is None:
        fail(f"no Manifest.plist/xml under {info}")
    print(f"SOURCE {source}")
    flat = {}

    def walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    walk(value)
                else:
                    flat[str(key)] = value
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    serial = next((flat[k] for k in ("SerialNumber", "ProductSerialNumber", "serialNumber")
                   if k in flat and flat[k]), None)
    if not serial:
        fail(f"no serial key; keys={sorted(flat)[:20]}")
    print(f"SERIAL {serial}")
    for label, key in (("DEVICE_NAME", "DeviceName"), ("UDID", "UniqueDeviceID"),
                       ("PRODUCT_TYPE", "ProductType"), ("BUILD", "BuildVersion")):
        if key in flat:
            print(f"{label} {flat[key]}")


def find_chat_image(root, conversation_hash: str):
    """Return the chat image whose trailer is an OLE/CFB document, or None."""
    containers = Path(root) / "private" / "var" / "mobile" / "Containers" / "Data" / "Application"
    if not containers.is_dir():
        return None
    for image in containers.glob(f"*/Documents/*/Img/{conversation_hash}/*.pic"):
        data = image.read_bytes()
        start = data.find(b"\xd0\xcf\x11\xe0")
        if start >= 0:
            return image
    return None


def chat_password(db_path: str, table: str) -> str:
    """Return the last short alphanumeric message in the chat table."""
    import re

    con = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    try:
        messages = [str(r[0]).strip() for r in con.execute(f'SELECT Message FROM "{table}" ORDER BY CreateTime')]
    finally:
        con.close()
    code = next((m for m in reversed(messages) if re.fullmatch(r"[A-Za-z0-9]{6,16}", m)), "")
    if not code:
        fail(f"no short password text in {table}")
    return code


def chatpics(root) -> None:
    """List chat conversations that contain an image with an OLE/CFB trailer."""
    containers = Path(root) / "private" / "var" / "mobile" / "Containers" / "Data" / "Application"
    if not containers.is_dir():
        fail(f"not an iOS backup root: {root}")
    found = 0
    for image in containers.glob("*/Documents/*/Img/*/*.pic"):
        data_head = image.read_bytes()
        start = data_head.find(b"\xd0\xcf\x11\xe0")
        if start < 0:
            continue
        found += 1
        print(f"CONV {image.parent.name}\t{image.name}\t{image.stat().st_size}\tOLE@{start}")
    if not found:
        print("no chat image with an OLE trailer")


def exif(path: str) -> None:
    """Print an image's EXIF GPS as decimal degrees."""
    from PIL import Image

    image = Image.open(path)
    gps = image.getexif().get_ifd(0x8825)
    if not gps or 2 not in gps or 4 not in gps:
        fail(f"no GPS EXIF in {path}")

    def deg(value):
        return float(value[0]) + float(value[1]) / 60 + float(value[2]) / 3600

    lat, lon = deg(gps[2]), deg(gps[4])
    print(f"GPS {lat:.4f}{gps.get(1, 'N')},{lon:.4f}{gps.get(3, 'E')}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) == 3 and sys.argv[1] == "exif":
        exif(sys.argv[2])
        return
    if len(sys.argv) == 3 and sys.argv[1] == "chatpics":
        chatpics(sys.argv[2])
        return
    if len(sys.argv) == 3 and sys.argv[1] == "device":
        device(sys.argv[2])
        return
    if len(sys.argv) == 4 and sys.argv[1] == "notes":
        notes(sys.argv[2], sys.argv[3])
        return
    if len(sys.argv) == 5 and sys.argv[1] == "docprice":
        docprice(*sys.argv[2:])
        return
    if len(sys.argv) >= 3 and sys.argv[1] == "ledger":
        ledger(*sys.argv[2:])
        return
    if len(sys.argv) == 3 and sys.argv[1] == "apps":
        apps(sys.argv[2])
        return
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
