"""Offline Chrome/Chromium saved-password recovery for Linux evidence.

Chain:
  GNOME keyring (old keyring format, password required)
    -> "Chrome Safe Storage" secret
    -> PBKDF2-HMAC-SHA1(secret, "saltysalt", 1, 16)
    -> AES-128-CBC (IV = 16 spaces) decrypt Login Data v10/v11

The Login Data DB and keyring are copied/read only; the original evidence is
never modified. The keyring password is read from stdin or an env var, not from
argv, so it does not appear in process listings.

Usage:
  printf '%s' "$KEYRING_PASSWORD" | python -I chrome_login_decrypt.py \
    --login-data "<...>/Default/Login Data" \
    --keyring "<...>/.local/share/keyrings/默认密钥环.keyring" \
    --keyring-password-stdin --origin-filter dgy02

  # If the Safe Storage secret is already known:
  python -I chrome_login_decrypt.py --login-data ... --safe-storage-stdin
"""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import struct
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC = b"GnomeKeyring\n\r\0\n"
SALT = b"saltysalt"
IV = b" " * 16


class ParseError(RuntimeError):
    pass


class Cursor:
    def __init__(self, data):
        self.data = data
        self.o = 0

    def take(self, n):
        if self.o + n > len(self.data):
            raise ParseError(f"short read at {self.o}: need {n}, have {len(self.data) - self.o}")
        v = self.data[self.o:self.o + n]
        self.o += n
        return v

    def u16(self):
        return struct.unpack(">H", self.take(2))[0]

    def u32(self):
        return struct.unpack(">I", self.take(4))[0]

    def string(self):
        n = self.u32()
        if n == 0xFFFFFFFF:
            return None
        return self.take(n)


def derive_keyring_key(password: str, salt: bytes, iterations: int):
    """gnome-keyring old format: SHA256(pw+salt), then SHA256 iterated.

    The file stores iteration_count; the implementation hashes the initial
    digest iteration_count - 1 additional times.
    """
    d = hashlib.sha256(password.encode("utf-8") + salt).digest()
    for _ in range(max(0, iterations - 1)):
        d = hashlib.sha256(d).digest()
    return d[:16], d[16:32]


def parse_keyring(path: Path, password: str):
    data = path.read_bytes()
    if not data.startswith(MAGIC):
        raise ParseError("not a GNOME keyring file (bad magic)")
    c = Cursor(data)
    c.take(len(MAGIC))
    version = c.u16()
    crypto = c.take(1)[0]
    hash_type = c.take(1)[0]
    name = c.string()
    c.take(8)  # ctime
    c.take(8)  # mtime
    flags = c.u32()
    lock_timeout = c.u32()
    iterations = c.u32()
    salt = c.take(8)
    c.take(16)  # reserved
    num_items = c.u32()
    for _ in range(num_items):
        c.u32()  # id
        c.u32()  # type
        for _ in range(c.u32()):
            c.string()  # attr name
            typ = c.u32()
            if typ == 0:
                c.string()  # string hash
            else:
                c.u32()  # int hash
    enc_len = c.u32()
    enc = c.take(enc_len)

    key, iv = derive_keyring_key(password, salt, iterations)
    dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor().update(enc)
    if dec[:16] != hashlib.md5(dec[16:]).digest():
        # Some variants store iteration_count without the -1.
        key2, iv2 = derive_keyring_key(password, salt, iterations + 1)
        dec2 = Cipher(algorithms.AES(key2), modes.CBC(iv2)).decryptor().update(enc)
        if dec2[:16] == hashlib.md5(dec2[16:]).digest():
            dec = dec2
        else:
            raise ParseError("keyring password wrong or unsupported keyring crypto")
    body = dec[16:]
    bc = Cursor(body)
    items = []
    for _ in range(num_items):
        display_name = bc.string()
        secret = bc.string()
        bc.take(8 + 8)  # ctime, mtime
        bc.string()  # reserved_str
        bc.take(16)  # reserved_int2
        for _ in range(bc.u32()):
            bc.string()
            typ = bc.u32()
            if typ == 0:
                bc.string()
            else:
                bc.u32()
        for _ in range(bc.u32()):
            bc.u32()
            bc.string()
            bc.string()
            bc.string()
            bc.u32()
        items.append({
            "display_name": (display_name or b"").decode("utf-8", "replace"),
            "secret": (secret or b"").decode("utf-8", "replace"),
        })
    return {
        "version": version,
        "crypto": crypto,
        "hash": hash_type,
        "name": (name or b"").decode("utf-8", "replace"),
        "iterations": iterations,
        "items": items,
    }


def chrome_key(secret: str):
    return PBKDF2HMAC(
        algorithm=hashes.SHA1(), length=16, salt=SALT, iterations=1
    ).derive(secret.encode("utf-8"))


def unpad(data: bytes):
    if not data:
        return data
    p = data[-1]
    if 1 <= p <= 16 and data.endswith(bytes([p]) * p):
        return data[:-p]
    return data


def decrypt_login_data(login_data: Path, secret: str, origin_filter: str = ""):
    with tempfile.TemporaryDirectory(prefix="chrome_login_") as td:
        tmp = Path(td) / "Login Data"
        shutil.copy2(login_data, tmp)
        con = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT origin_url, username_value, password_value FROM logins"
        ).fetchall()
        con.close()
    keys = [chrome_key(secret), chrome_key("peanuts")]
    out = []
    for origin, username, blob in rows:
        if origin_filter and origin_filter.lower() not in (origin or "").lower():
            continue
        blob = bytes(blob or b"")
        password = None
        note = ""
        if blob[:3] in (b"v10", b"v11"):
            ct = blob[3:]
            for k in keys:
                if len(ct) % 16:
                    note = "ciphertext not block-aligned"
                    continue
                dec = Cipher(algorithms.AES(k), modes.CBC(IV)).decryptor().update(ct)
                pt = unpad(dec)
                if pt and all(32 <= b < 127 or b >= 0x80 for b in pt):
                    try:
                        password = pt.decode("utf-8")
                        break
                    except UnicodeDecodeError:
                        continue
            if password is None:
                note = note or "v10/v11 decrypt failed"
        elif blob:
            note = "unsupported prefix (Windows DPAPI/other)"
        out.append({
            "origin": origin,
            "username": username,
            "password": password,
            "note": note,
        })
    return out


def read_stdin():
    return sys.stdin.read().strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login-data", required=True)
    ap.add_argument("--keyring", default="")
    ap.add_argument("--keyring-password-stdin", action="store_true")
    ap.add_argument("--keyring-password-env", default="CHROME_KEYRING_PASSWORD")
    ap.add_argument("--safe-storage-stdin", action="store_true")
    ap.add_argument("--safe-storage-env", default="CHROME_SAFE_STORAGE")
    ap.add_argument("--origin-filter", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--show-safe-storage", action="store_true")
    args = ap.parse_args()

    secret = ""
    if args.safe_storage_stdin:
        secret = read_stdin()
    elif os.environ.get(args.safe_storage_env):
        secret = os.environ[args.safe_storage_env]

    if args.keyring:
        if args.keyring_password_stdin:
            password = read_stdin()
        elif os.environ.get(args.keyring_password_env):
            password = os.environ[args.keyring_password_env]
        else:
            print("missing keyring password: use --keyring-password-stdin or env", file=sys.stderr)
            return 2
        kr = parse_keyring(Path(args.keyring), password)
        for item in kr["items"]:
            if "safe storage" in item["display_name"].lower() or "chrome" in item["display_name"].lower():
                secret = item["secret"]
                break
        if not secret:
            secret = next((i["secret"] for i in kr["items"] if i["secret"]), "")
        if args.show_safe_storage:
            print(json.dumps({"keyring_name": kr["name"], "items": kr["items"]}, ensure_ascii=False))
    if not secret:
        print("missing Safe Storage secret: pass --keyring or --safe-storage-stdin", file=sys.stderr)
        return 2

    rows = decrypt_login_data(Path(args.login_data), secret, args.origin_filter)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(f"origin={r['origin']}\tusername={r['username']}\tpassword={r['password']}\tnote={r['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
