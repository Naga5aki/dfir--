"""Summarize extracted expert packages. Read-only; no code from archives is executed."""
from __future__ import annotations

import hashlib
import struct
import zipfile
from pathlib import Path

BASE = Path(r"D:\ForensicsAgent\_hexp_review_20261106")
TRAFFIC = Path(r"D:\Desktop\_zip_traffic-forensics.hexp.zip")
WMX = Path(r"D:\Desktop\_zip_wmx-bill-analysis-expert.hexp.zip")
OUT = Path(r"D:\ForensicsAgent\_hexp_review_scripts\summary.txt")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png_info(data: bytes) -> str:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return f"not-png magic={data[:8]!r} len={len(data)}"
    # IHDR
    length = struct.unpack(">I", data[8:12])[0]
    ctype = data[12:16]
    if ctype != b"IHDR" or length < 13:
        return f"png-no-ihdr len={len(data)}"
    w, h, bit, color = struct.unpack(">IIBB", data[16:26])
    return f"{w}x{h} bit={bit} color={color} bytes={len(data)}"


lines: list[str] = []
lines.append("== nested zip compare ==")
with zipfile.ZipFile(TRAFFIC) as zf:
    nested = zf.read("_zip_wmx-bill-analysis-expert.hexp.zip")
standalone = WMX.read_bytes()
lines.append(f"nested_size={len(nested)} sha256={sha256(nested)}")
lines.append(f"standalone_size={len(standalone)} sha256={sha256(standalone)}")
lines.append(f"byte_identical={nested == standalone}")
if nested != standalone:
    # compare member crcs
    import io

    with zipfile.ZipFile(io.BytesIO(nested)) as a, zipfile.ZipFile(io.BytesIO(standalone)) as b:
        an = a.namelist()
        bn = b.namelist()
        lines.append(f"nested_names={an}")
        lines.append(f"standalone_names={bn}")
        lines.append(f"names_equal={an == bn}")

lines.append("")
lines.append("== avatars ==")
for png in sorted(BASE.rglob("avatar.png")):
    data = png.read_bytes()
    rel = png.relative_to(BASE).as_posix()
    lines.append(f"{rel}: {png_info(data)} sha256={sha256(data)}")

lines.append("")
lines.append("== expert frontmatter keys ==")
for md in sorted(BASE.rglob("EXPERT.md")):
    text = md.read_text(encoding="utf-8-sig")
    rel = md.relative_to(BASE).as_posix()
    if not text.startswith("---"):
        lines.append(f"{rel}: NO FRONTMATTER")
        continue
    end = text.find("\n---", 3)
    fm = text[3:end]
    keys = []
    for line in fm.splitlines():
        if line and not line.startswith(" ") and ":" in line:
            keys.append(line.split(":", 1)[0])
    lines.append(f"{rel}: {', '.join(keys)}")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(OUT)
