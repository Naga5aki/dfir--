"""Read-only checks and one-shot backups for the hexp import.

Does not modify profiles except when backup_touched copies listed files
into a new destination. Refuses to overwrite an existing destination.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

HERMES = Path(r"D:\ForensicsAgent\hermes")
REPO = Path(r"D:\ForensicsAgent")
LIBRARY = HERMES / "skill-library" / "dfir-curated" / "20261107-hexp"
MAP_PATH = LIBRARY / "profile-map.json"
PROFILES = HERMES / "profiles"

FORBIDDEN = (
    "ges status",
    "ges case",
    "ges read",
    "ges ls",
    "Goldeneyes://",
    "thunder-app-",
    "survey_binary",
    "ida_pro_mcp",
    "SetBreakpoint",
    "LoadBinary",
    "pywmxclient",
    "clonezilla-to-e01",
)


def forbidden_hits(text: str) -> list[str]:
    """Return product-tool names used as callable steps.

    A line that says the tool is not connected and must not be called is
    not a hit. ``create-vm`` counts only when that line does not say
    ``不要调用``.
    """
    hits: list[str] = []
    lines = text.splitlines() or [text]
    for line in lines:
        if "未接入，不要调用" in line:
            continue
        for token in FORBIDDEN:
            if token in line and token not in hits:
                hits.append(token)
        if "create-vm" in line and "不要调用" not in line and "create-vm" not in hits:
            hits.append("create-vm")
    return hits


def _relative(path: Path) -> Path:
    resolved = path.resolve()
    for root in (HERMES, REPO):
        try:
            return resolved.relative_to(root.resolve())
        except ValueError:
            continue
    return Path(path.name)


def backup_touched(dest: Path, paths: list[Path]) -> None:
    """Copy ``paths`` under ``dest``, preserving repo-relative structure.

    ``dest`` must not already exist. Exit code 2 if it does.
    """
    dest = Path(dest)
    if dest.exists():
        raise SystemExit(2)
    dest.mkdir(parents=True)
    for path in paths:
        path = Path(path)
        if not path.exists():
            raise SystemExit(2)
        target = dest / _relative(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copy2(path, target)


def check_profile_map(map_path: Path | None = None) -> list[str]:
    """Compare library sources to the profile copies named in the map.

    Returns short issue strings. Does not print file contents.
    """
    map_path = Path(map_path) if map_path else MAP_PATH
    if not map_path.is_file():
        return ["source profile-map.json missing"]
    data = json.loads(map_path.read_text(encoding="utf-8"))
    library = map_path.parent
    issues: list[str] = []
    for entry in data.get("files", []):
        source = library / entry["source"]
        dest_rel = entry["dest"]
        if not source.is_file():
            issues.append(f"source {entry['source']} missing")
            continue
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        source_hits = forbidden_hits(source.read_text(encoding="utf-8"))
        if source_hits:
            issues.append(f"source {entry['source']} forbidden")
        for profile in entry["profiles"]:
            dest = PROFILES / profile / dest_rel
            if not dest.is_file():
                issues.append(f"{profile} {dest_rel} missing")
                continue
            if hashlib.sha256(dest.read_bytes()).hexdigest() != source_hash:
                issues.append(f"{profile} {dest_rel} hash")
            if forbidden_hits(dest.read_text(encoding="utf-8")):
                issues.append(f"{profile} {dest_rel} forbidden")
    for profile in ("dfir-myos", "dfir-max"):
        soul = PROFILES / profile / "SOUL.md"
        if soul.is_file() and "query_phone_file_forensics_result_summary" in soul.read_text(encoding="utf-8"):
            issues.append(f"{profile} SOUL.md ghost-tool")
    return issues


def main() -> int:
    issues = check_profile_map()
    for issue in issues:
        print(issue)
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
