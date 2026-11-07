"""Search small text-like files on the phone mount for question keywords."""
from pathlib import Path

ROOT = Path(r"C:\osmap\33C807FADC8E48CBB4117B7DB380B67B_20261107101136\Root\data")
KEYS = ("接头暗号", "开机密码", "电脑密码", "秘钥环", "最重要", "李", "欠款", "欠条")
OUT = Path(r"D:\ForensicsAgent\.superpowers\sdd\2026-11-07-hexp-dfir-capability\kw_hits.txt")
SUFFIX = {".xml", ".txt", ".json", ".db", ".cfg", ".ini", ".html", ".js"}


def main() -> None:
    lines = []
    scanned = 0
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUFFIX and path.suffix != "":
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > 2_000_000 or size == 0:
            continue
        scanned += 1
        try:
            blob = path.read_bytes()
        except OSError:
            continue
        text = blob.decode("utf-8", errors="ignore")
        if not any(k in text for k in KEYS):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if any(k in line for k in KEYS):
                lines.append(f"{path}:{i}:{line.strip()[:240]}")
                if len(lines) > 80:
                    break
        if len(lines) > 80:
            break
    lines.append(f"scanned {scanned}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT, len(lines))

if __name__ == "__main__":
    main()
