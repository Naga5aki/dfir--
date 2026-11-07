"""Extract untrusted .hexp.zip archives into a new directory and dump text.

Does not execute anything from the archives. Refuses to overwrite an existing dest.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

BASE = Path(r"D:\ForensicsAgent\_hexp_review_20261106")
ARCHIVES = [
    Path(r"D:\Desktop\_zip_apk-analysis-expert.hexp.zip"),
    Path(r"D:\Desktop\_zip_electronic-data-forensics-record-drafting.hexp.zip"),
    Path(r"D:\Desktop\_zip_exe-reversing.hexp.zip"),
    Path(r"D:\Desktop\_zip_goldeneyes-forensics.hexp.zip"),
    Path(r"D:\Desktop\_zip_memory-forensics.hexp.zip"),
    Path(r"D:\Desktop\_zip_server-forensics-expert.hexp.zip"),
    Path(r"D:\Desktop\_zip_traffic-forensics.hexp.zip"),
    Path(r"D:\Desktop\_zip_wmx-bill-analysis-expert.hexp.zip"),
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_member_name(name: str) -> str | None:
    name = name.replace("\\", "/")
    if name.startswith("/") or name.startswith("../") or "/../" in name or name == "..":
        return None
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if any(p == ".." or ":" in p for p in parts):
        return None
    return "/".join(parts) + ("/" if name.endswith("/") else "")


def main() -> int:
    if BASE.exists():
        print("dest exists, refuse to overwrite:", BASE, file=sys.stderr)
        return 2
    BASE.mkdir(parents=True)
    report = []
    for archive in ARCHIVES:
        raw = archive.read_bytes()
        dest = BASE / archive.stem
        dest.mkdir()
        entry = {
            "archive": str(archive),
            "archive_size": archive.stat().st_size,
            "archive_sha256": sha256(raw),
            "members": [],
        }
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                name = safe_member_name(info.filename)
                if name is None:
                    entry["members"].append({"name": info.filename, "rejected": "unsafe-path"})
                    continue
                data = zf.read(info)
                out = dest.joinpath(*[p for p in name.split("/") if p])
                if name.endswith("/"):
                    out.mkdir(parents=True, exist_ok=True)
                else:
                    if out.exists():
                        entry["members"].append({"name": name, "rejected": "exists"})
                        continue
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(data)
                entry["members"].append(
                    {
                        "name": name,
                        "size": info.file_size,
                        "compress_size": info.compress_size,
                        "date_time": list(info.date_time),
                        "flag_bits": info.flag_bits,
                        "compress_type": info.compress_type,
                        "crc": f"{info.CRC:08x}",
                        "sha256": None if name.endswith("/") else sha256(data),
                        "external_attr": info.external_attr,
                        "create_system": info.create_system,
                    }
                )
        report.append(entry)

    (BASE / "_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    chunks: list[str] = []
    for root, _dirs, fnames in os.walk(BASE):
        for fn in sorted(fnames):
            fp = Path(root) / fn
            if fp.name == "_manifest.json":
                continue
            if fp.suffix.lower() not in {".md", ".py", ".txt", ".yml", ".yaml", ".json"}:
                continue
            rel = fp.relative_to(BASE).as_posix()
            blob = fp.read_bytes()
            text = None
            used = None
            for enc in ("utf-8-sig", "utf-8", "gbk"):
                try:
                    text = blob.decode(enc)
                    used = enc
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                chunks.append(f"\n\n===== {rel} UNDECODABLE bytes={len(blob)} =====\n")
                continue
            chunks.append(f"\n\n===== {rel}  enc={used}  bytes={len(blob)} =====\n")
            chunks.append(text)
    out_text = BASE / "_all_text.md"
    out_text.write_text("".join(chunks), encoding="utf-8")
    print("OK", BASE)
    print("text_bytes", out_text.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
