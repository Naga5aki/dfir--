#!/usr/bin/env python3
"""com.aijiami.cn 文件解密（AES-256-CBC，key=SHA256(密码)，IV="juhetianji123456"，PKCS7）。

为什么要它：本检材的直播素材被该工具加密成 *.tmp.encrypted，必须先解密才能抽帧/扫码。
只读源文件；输出写到指定目录（不要写检材目录）。

用法：
  python aijiami_decrypt.py <加密文件> <输出文件> <密码>
  python aijiami_decrypt.py <加密文件> --probe <密码>     # 只解前 64 字节验证密码是否正确
"""
import hashlib
import sys
from pathlib import Path

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

IV = b"juhetianji123456"


def make_cipher(password: str):
    key = hashlib.sha256(password.encode("utf-8")).digest()
    return Cipher(algorithms.AES(key), modes.CBC(IV)).decryptor(), key


def probe(src: Path, password: str) -> dict:
    dec, key = make_cipher(password)
    with src.open("rb") as f:
        head = f.read(64)
    out = dec.update(head[:48])  # 48 = 3 个 AES 块
    ok = out[4:8] in (b"ftyp", b"moov", b"mdat") or out[:4] in (b"\x00\x00\x00\x18", b"\x00\x00\x00\x20")
    return {"password": password, "key_hex": key.hex(), "head_hex": out[:16].hex(),
            "looks_like_mp4": bool(ok), "ascii": "".join(chr(b) if 32 <= b < 127 else "." for b in out[:24])}


def decrypt(src: Path, dst: Path, password: str) -> dict:
    dec, key = make_cipher(password)
    total = src.stat().st_size
    dst.parent.mkdir(parents=True, exist_ok=True)
    buf = bytearray()
    written = 0
    with src.open("rb") as fin, dst.open("wb") as fout:
        while True:
            chunk = fin.read(4 * 1024 * 1024)
            if not chunk:
                break
            buf.extend(chunk)
            usable = (len(buf) // 16) * 16
            if usable:
                fout.write(dec.update(bytes(buf[:usable])))
                written += usable
                del buf[:usable]
        if buf:
            return {"ok": False, "error": f"密文长度不是 16 的倍数，尾部 {len(buf)} 字节未处理"}
        padder = padding.PKCS7(128).unpadder()
        tail = b""
        # 末块去填充：重解最后一个块不方便，改为重新读末 16 字节直接算
        with dst.open("r+b") as fout:
            fout.seek(max(0, written - 16))
            last_plain = fout.read(16)
            fout.seek(max(0, written - 16))
            try:
                tail = padder.update(last_plain) + padder.finalize()
                fout.write(tail)
                fout.truncate()
            except ValueError:
                pass
    return {"ok": True, "src_bytes": total, "out_bytes": dst.stat().st_size, "key_hex": key.hex()}


def main():
    args = sys.argv[1:]
    if len(args) < 3:
        print(__doc__)
        return 2
    src = Path(args[0])
    if not src.is_file():
        print(f"文件不存在: {src}")
        return 2
    if args[1] == "--probe":
        for pwd in args[2:]:
            r = probe(src, pwd)
            print(f"{r['password']} | mp4={r['looks_like_mp4']} | ascii={r['ascii']} | head={r['head_hex']}")
        return 0
    dst = Path(args[1])
    r = decrypt(src, dst, args[2])
    print(r)
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
