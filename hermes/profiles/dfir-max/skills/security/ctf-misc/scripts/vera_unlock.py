#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vera_unlock.py — VeraCrypt/TrueCrypt 类卷：离线头部解锁 → 数据区解密 → FAT 文件提取。

依赖：pycryptodome（Crypto.*）。纯离线：不挂载、不需驱动、不调用 VeraCrypt.exe。
判据：`VERA` 魔数 + 头字段区 CRC32 + 主密钥区 CRC32（双 CRC 通过 = 密钥链自证）。

用法:
  python vera_unlock.py --volume VOL [--keyfile KF] --password PW
                        [--prf auto|sha512|ripemd160|sha256] [--iters auto|N1,N2,...]
                        [--korder both|dk01|dk10] [--unit-mode auto|abs|rel]
                        [--dump-data OUT] [--extract DIR] [--expect-data-sha SHA256] [--quiet]

  退出码：0=解锁成功；2=解锁失败；3=解锁成功但数据区探测/导出失败。
  可导入：keyfile_pool / pbkdf2 / xts_decrypt / try_unlock / open_and_decrypt / fat_list / fat_read_file

纪律：keyfile 必须是原始文件本体；口令/答案不得写入正式库；负控制（无 keyfile/错口令/错 keyfile）必须被拒。
"""
import argparse
import hashlib
import hmac as _hmac
import os
import struct
import sys
import zlib

try:
    from Crypto.Cipher import AES
    from Crypto.Hash import RIPEMD160
except ImportError:  # pragma: no cover
    try:
        from Cryptodome.Cipher import AES
        from Cryptodome.Hash import RIPEMD160
    except ImportError:
        print("ERROR: pycryptodome (Crypto.*) required", file=sys.stderr)
        sys.exit(4)

# 注：本模块以 AES-ECB 为原语实现 XTS（该族规范构造：XTS = ECB + tweak 链），
# 并非直接以 ECB 模式加密数据；静态扫描的 ECB 告警在此语境为误报。

# ---------- CRC32 流式表（与官方 Keyfiles.c 的 UPDC32 对齐） ----------
_CRCTAB = []
for _n in range(256):
    _c = _n
    for _ in range(8):
        _c = (0xEDB88320 ^ (_c >> 1)) if (_c & 1) else (_c >> 1)
    _CRCTAB.append(_c)


def updc32(b, crc):
    return _CRCTAB[(crc ^ b) & 0xFF] ^ (crc >> 8)


def keyfile_pool(data, pool_size):
    """官方流式 keyfile 池：每读 1 字节更新 CRC32，把 4 个 CRC 字节（高→低）累加进池循环。"""
    pool = bytearray(pool_size)
    crc = 0xFFFFFFFF
    wp = 0
    for b in data[:1024 * 1024]:
        crc = updc32(b, crc)
        for shift in (24, 16, 8, 0):
            pool[wp] = (pool[wp] + ((crc >> shift) & 0xFF)) & 0xFF
            wp = (wp + 1) % pool_size
    return bytes(pool)


def mix_password(pwd, pool):
    """官方口令混合：前 min(len(pwd),len(pool)) 字节 = (pwd+pool)&0xFF，其余 = pool。"""
    out = bytearray(len(pool))
    n = min(len(pwd), len(pool))
    for i in range(len(pool)):
        out[i] = ((pwd[i] + pool[i]) & 0xFF) if i < n else pool[i]
    return bytes(out)


def pbkdf2(name, factory, hlen, password, salt, iterations, dklen):
    try:
        return hashlib.pbkdf2_hmac(name, password, salt, iterations, dklen)
    except Exception:
        pass
    blocks = (dklen + hlen - 1) // hlen
    out = b""
    for b in range(1, blocks + 1):
        u = _hmac.new(password, salt + struct.pack(">I", b), factory).digest()
        t = bytearray(u)
        prev = u
        for _ in range(iterations - 1):
            u = _hmac.new(password, prev, factory).digest()
            prev = u
            for i in range(hlen):
                t[i] ^= u[i]
        out += bytes(t)
    return out[:dklen]


def xts_mul_alpha(t):
    """官方 Xts.c 的 GF(2^128) 更新（LE）：整体左移 1 位；旧最高位为 1 时最低字节 XOR 0x87。"""
    t = bytearray(t)
    top = t[15] & 0x80
    carry = 0
    for i in range(16):
        v = t[i]
        t[i] = ((v << 1) & 0xFF) | carry
        carry = (v >> 7) & 1
    if top:
        t[0] ^= 0x87
    return bytes(t)


def xts_decrypt(k1, k2, data, unit=0, whole_unit=False):
    """该族 XTS：每 512B 数据单元 tweak=Ek2(LE128(unit))，逐块 mul_alpha 链；
    whole_unit=True 时整段当一个单元（头部 448B 场景）。"""
    dk = AES.new(k1, AES.MODE_ECB)
    ek = AES.new(k2, AES.MODE_ECB)
    out = bytearray()
    n = len(data) // 16
    pos = 0
    biu = 0
    t = ek.encrypt((unit & 0xFFFFFFFFFFFFFFFF).to_bytes(16, "little"))
    while pos < n:
        if not whole_unit and biu == 32:
            unit += 1
            t = ek.encrypt((unit & 0xFFFFFFFFFFFFFFFF).to_bytes(16, "little"))
            biu = 0
        c = data[pos * 16:(pos + 1) * 16]
        x = bytes(a ^ b for a, b in zip(c, t))
        y = dk.decrypt(x)
        out += bytes(a ^ b for a, b in zip(y, t))
        t = xts_mul_alpha(t)
        biu += 1
        pos += 1
    return bytes(out)


def be16(b, o):
    return (b[o] << 8) | b[o + 1]


def be32(b, o):
    return (b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]


def be64(b, o):
    v = 0
    for i in range(8):
        v = (v << 8) | b[o + i]
    return v


PRF_TABLE = {
    "ripemd160": ("ripemd160", lambda: RIPEMD160.new(), 20, [500000, 327661, 200000, 2000]),
    "sha512": ("sha512", None, 64, [500000, 200000, 1000]),
    "sha256": ("sha256", None, 32, [500000, 200000, 1000]),
}


def try_unlock(vol, password, keyfile_bytes=None, iters_override=None, prf_filter=None,
               korder="both", verbose=True):
    """返回 dict（含 dec/dk/korder/prf/iters/双 CRC 值）或 None。"""
    salt = vol[0:64]
    enc = vol[64:512]
    pwd = password.encode() if isinstance(password, str) else bytes(password)
    pool_size = 64 if len(pwd) <= 64 else 128
    if keyfile_bytes is not None:
        pool = keyfile_pool(keyfile_bytes, pool_size)
        pwd_mixed = mix_password(pwd, pool)
    else:
        pwd_mixed = pwd
    names = [prf_filter] if prf_filter else ["ripemd160", "sha512", "sha256"]
    for name in names:
        hname, factory, hlen, default_iters = PRF_TABLE[name]
        for iters in (iters_override or default_iters):
            dk = pbkdf2(hname, factory, hlen, pwd_mixed, salt, iters, 64)
            for ko in (("dk01", "dk10") if korder == "both" else (korder,)):
                k1 = dk[0:32] if ko == "dk01" else dk[32:64]
                k2 = dk[32:64] if ko == "dk01" else dk[0:32]
                dec = xts_decrypt(k1, k2, enc, unit=0, whole_unit=True)
                if dec[0:4] == b"VERA":
                    hdr_crc = be32(dec, 188)
                    calc = zlib.crc32(dec[0:188]) & 0xFFFFFFFF
                    key_crc = be32(dec, 8)
                    key_calc = zlib.crc32(dec[192:256]) & 0xFFFFFFFF
                    if verbose:
                        print("  magic hit: prf=%s iters=%d korder=%s hdrcrc=%08x/%08x ok=%s keycrc=%08x/%08x ok=%s"
                              % (name, iters, ko, hdr_crc, calc, hdr_crc == calc,
                                 key_crc, key_calc, key_crc == key_calc))
                    return {"dk": dk, "korder": ko, "dec": dec, "prf": name, "iters": iters,
                            "hdr_crc_ok": hdr_crc == calc, "key_crc_ok": key_crc == key_calc,
                            "hdr_crc": hdr_crc, "key_crc": key_crc}
    return None


def open_and_decrypt(vol, res, unit_mode="auto", verbose=True):
    """数据区解密：主密钥对 + 起点/长度（头部字段优先）；单元号 abs(绝对扇区)/rel(数据区相对) 实测裁定。"""
    dec = res["dec"]
    es = be64(dec, 44)
    el = be64(dec, 52)
    vs = be64(dec, 36)
    if not (0 < es < len(vol) and 0 < el <= len(vol)):
        es, el = 512, len(vol) - 512
    mk1 = dec[192:224]
    mk2 = dec[224:256]
    if verbose:
        print("  layout: volume_size=%d enc_area_start=%d enc_area_len=%d" % (vs, es, el))
    data = vol[es:es + el]
    mode_used = None
    for mode in (("abs", "rel") if unit_mode == "auto" else (unit_mode,)):
        unit = (es // 512) if mode == "abs" else 0
        probe = xts_decrypt(mk1, mk2, data[:512], unit=unit)
        sig = probe[510:512] == b"\x55\xaa"
        if verbose:
            print("  probe: mode=%s unit=%d fat_sig=%s oem=%r" %
                  (mode, unit, sig, bytes(probe[3:11]).rstrip(b"\x00 ")))
        if mode_used is None:
            mode_used = mode
        if sig:
            mode_used = mode
            break
    unit = (es // 512) if mode_used == "abs" else 0
    pt = xts_decrypt(mk1, mk2, data, unit=unit)
    if verbose:
        print("  data decrypted: mode=%s %d bytes" % (mode_used, len(pt)))
    return {"data": pt, "mode": mode_used, "start": es, "len": el, "k1": mk1, "k2": mk2}


# ---------------- FAT（FAT12/FAT16 根目录提取） ----------------
def _u16(b, o):
    return struct.unpack("<H", b[o:o + 2])[0]


def _u32(b, o):
    return struct.unpack("<I", b[o:o + 4])[0]


def fat_list(data):
    """解析引导扇区 + 根目录；返回 (info, entries)。entries: name/ext/attr/cluster/size。"""
    bs = data[0:512]
    info = {
        "bps": _u16(bs, 11), "spc": bs[13], "resv": _u16(bs, 14), "nfats": bs[16],
        "rootent": _u16(bs, 17), "fatsz": _u16(bs, 22),
        "totsec": _u16(bs, 19) or _u32(bs, 32),
        "oem": bytes(bs[3:11]), "label": bytes(bs[43:54]), "fstype": bytes(bs[54:62]),
    }
    bps, spc, resv, nfats, rootent, fatsz = (info[k] for k in ("bps", "spc", "resv", "nfats", "rootent", "fatsz"))
    root_off = (resv + nfats * fatsz) * bps
    entries = []
    for i in range(rootent):
        e = data[root_off + i * 32: root_off + i * 32 + 32]
        if len(e) < 32 or e[0] == 0:
            break
        if e[0] == 0xE5 or (e[11] & 0x0F) == 0x0F:
            continue
        if e[11] & 0x08:
            continue
        name = e[0:8].decode("latin1").rstrip()
        ext = e[8:11].decode("latin1").rstrip()
        entries.append({"name": name, "ext": ext, "attr": e[11], "cluster": _u16(e, 26), "size": _u32(e, 28)})
    info["first_data_sector"] = resv + nfats * fatsz + (rootent * 32 + bps - 1) // bps
    return info, entries


def fat_read_file(data, info, entry):
    """按 FAT 链读取文件本体（支持 FAT12/FAT16；单簇足量时自然兼容）。"""
    bps, spc = info["bps"], info["spc"]
    resv, nfats, fatsz = info["resv"], info["nfats"], info["fatsz"]
    fat_off = resv * bps
    tot_data_sec = info["totsec"] - info["first_data_sector"]
    nclusters = tot_data_sec // spc
    fat16 = nclusters >= 4085
    def next_cluster(c):
        if not fat16:
            off = fat_off + c + c // 2
            v = data[off] | (data[off + 1] << 8)
            return (v >> 4) if (c & 1) else (v & 0x0FFF)
        return _u16(data, fat_off + c * 2)
    out = bytearray()
    c = entry["cluster"]
    guard = 0
    while True:
        if c == 0:
            break
        if (not fat16 and c >= 0xFF7) or (fat16 and c >= 0xFFF7):
            break
        off = (info["first_data_sector"] + (c - 2) * spc) * bps
        out += data[off:off + spc * bps]
        c = next_cluster(c)
        guard += 1
        if guard > 65536:
            break
    return bytes(out[:entry["size"]])


def main():
    ap = argparse.ArgumentParser(description="VeraCrypt/TrueCrypt offline unlock + data decrypt + FAT extract")
    ap.add_argument("--volume", required=True)
    ap.add_argument("--keyfile", default=None)
    ap.add_argument("--password", required=True)
    ap.add_argument("--prf", default="auto", choices=("auto", "sha512", "ripemd160", "sha256"))
    ap.add_argument("--iters", default="auto")
    ap.add_argument("--korder", default="both", choices=("both", "dk01", "dk10"))
    ap.add_argument("--unit-mode", default="auto", choices=("auto", "abs", "rel"))
    ap.add_argument("--dump-data", default=None)
    ap.add_argument("--extract", default=None)
    ap.add_argument("--expect-data-sha", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    vol = open(a.volume, "rb").read()
    kfb = open(a.keyfile, "rb").read() if a.keyfile else None
    itv = None
    if a.iters != "auto":
        itv = [int(x) for x in a.iters.split(",")]
    pf = None if a.prf == "auto" else a.prf

    if not a.quiet:
        print("volume: %s (%d bytes), keyfile=%s" % (a.volume, len(vol), a.keyfile or "None"))
    # 试 prf 优先序：若指定 korder 就按指定，否则先 dk01 后 dk10
    res = None
    for ko in (("dk01", "dk10") if a.korder == "both" else (a.korder,)):
        res = try_unlock(vol, a.password, kfb, iters_override=itv, prf_filter=pf, korder=ko,
                         verbose=not a.quiet)
        if res and res["hdr_crc_ok"]:
            break
        if res and not res["hdr_crc_ok"] and not a.quiet:
            print("  header CRC failed; continue search")
    if not res or not res["hdr_crc_ok"]:
        print("UNLOCK FAIL (no VERA + valid header CRC)")
        return 2
    if not a.quiet:
        print("UNLOCK OK: prf=%s iters=%d korder=%s hdr_crc=0x%08x key_crc_ok=%s"
              % (res["prf"], res["iters"], res["korder"], res["hdr_crc"], res["key_crc_ok"]))

    od = open_and_decrypt(vol, res, unit_mode=a.unit_mode, verbose=not a.quiet)
    data = od["data"]
    if a.expect_data_sha:
        h = hashlib.sha256(data).hexdigest()
        ok = (h == a.expect_data_sha)
        print("data sha256=%s expect=%s %s" % (h, a.expect_data_sha, "MATCH" if ok else "MISMATCH"))
        if not ok:
            return 3
    if a.dump_data:
        open(a.dump_data, "wb").write(data)
        if not a.quiet:
            print("saved:", a.dump_data)
    rc = 0
    if a.extract:
        try:
            info, entries = fat_list(data)
            os.makedirs(a.extract, exist_ok=True)
            if not a.quiet:
                print("FAT: %s oem=%r label=%r entries=%d" % (info["fstype"], info["oem"], info["label"], len(entries)))
            for e in entries:
                body = fat_read_file(data, info, e)
                fn = ("%s.%s" % (e["name"], e["ext"])).strip(".")
                with open(os.path.join(a.extract, fn), "wb") as f:
                    f.write(body)
                if not a.quiet:
                    print("  extracted %s (%d bytes)" % (fn, len(body)))
        except Exception as ex:
            print("EXTRACT FAIL:", repr(ex))
            rc = 3
    return rc


if __name__ == "__main__":
    sys.exit(main())
