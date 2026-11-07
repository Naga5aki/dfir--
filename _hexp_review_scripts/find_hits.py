"""Find a few named evidence files on the mounted images. No content dump."""
from pathlib import Path

ROOTS = [
    Path(r"C:\osmap\33C807FADC8E48CBB4117B7DB380B67B_20261107101136\Root"),
    Path(r"C:\osmap\3D5E708F0E864AFDB5BD86372B8818F1_20261107101156\Root"),
]
WANTED = {
    "settings_global.xml",
    "settings_secure.xml",
    "settings_system.xml",
    "note.db",
    "EnMicroMsg.db",
    "MicroMsg.db",
    "auth_info_key_prefs.xml",
    "CompatibleInfo.cfg",
}
NAME_PARTS = ("欠条", "note.db", "EnMicroMsg", "settings_global", "settings_secure")
OUT = Path(r"D:\ForensicsAgent\.superpowers\sdd\2026-11-07-hexp-dfir-capability\hits.txt")


def main() -> None:
    hits = []
    for root in ROOTS:
        hits.append(f"# {root} exists={root.exists()}")
        if not root.exists():
            continue
        count = 0
        for path in root.rglob("*"):
            count += 1
            if count > 200000:
                hits.append("STOPPED at 200000")
                break
            name = path.name
            if name in WANTED or any(part in name for part in NAME_PARTS):
                try:
                    size = path.stat().st_size
                except OSError:
                    size = -1
                hits.append(f"{size}\t{path}")
        hits.append(f"scanned {count}")
    OUT.write_text("\n".join(hits), encoding="utf-8")
    print(OUT, len(hits))

if __name__ == "__main__":
    main()
