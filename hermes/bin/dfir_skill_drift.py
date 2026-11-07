"""Report-only integrity check for a versioned source and six local skill copies.

Use an existing Python with ``-B``::

    python -B dfir_skill_drift.py --profiles-root <profiles> --source <version-dir>

The source's manifest.json is {"version": "...", "files": {relative_path: sha256}}.
Paths use forward slashes and are confined to skills/security/<skill>/... or
skills/forensics/<skill>/.... Bundled scripts, references, JSON and fixtures are
checked when listed. Unlisted files and other profiles are never enumerated.

Exit 0: match; 1: runtime drift; 2: invalid source/input or unsafe/unreadable path.
Output contains only profile, relative path and issue; never contents or hashes.
There is no repair mode and this module does not import or invoke Hermes.
An explicit source/root is a trust boundary. Use a quiet maintenance window:
this read-only comparison is not a lock against concurrent file replacement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat


PROFILES = ("dfir", "dfir-myos", "dfir-re", "dfir-mem", "dfir-pcap", "dfir-max")
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")
_RESERVED_WINDOWS = frozenset({
    "con", "prn", "aux", "nul", "conin$", "conout$",
    *("com" + str(i) for i in range(1, 10)),
    *("lpt" + str(i) for i in range(1, 10)),
    "com¹", "com²", "com³", "lpt¹", "lpt²", "lpt³",
})
_RUNTIME_COMPONENTS = frozenset({
    "env", "venv", ".venv", "__pycache__", ".cache", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".runtime-cache", "usage", "usage.json",
    "usage.jsonl", "usage.log",
})


def _finding(profile: str, relative: str, issue: str) -> dict:
    return {"profile": profile, "path": relative, "issue": issue}


def _source_error(relative: str = "manifest.json") -> dict:
    return _finding("source", relative, "source_invalid")


def _manifest_parts(relative: str) -> tuple[str, ...]:
    """Validate before joining: reject Windows aliases as well as traversal."""
    if not isinstance(relative, str) or len(relative) > 2048 or "\\" in relative:
        raise ValueError("invalid_manifest_path")
    parts = tuple(relative.split("/"))
    if len(parts) < 4 or parts[:2] not in (("skills", "security"), ("skills", "forensics")):
        raise ValueError("invalid_manifest_scope")
    for component in parts:
        lower = component.casefold()
        if (
            not component or component in (".", "..")
            or component[-1:] in (".", " ")
            or any(ord(char) < 32 or char in '<>:"|?*' for char in component)
            or lower.split(".")[0] in _RESERVED_WINDOWS
            or lower == ".env" or lower.startswith(".env.")
            or lower in _RUNTIME_COMPONENTS or lower.endswith((".pyc", ".pyo"))
        ):
            raise ValueError("invalid_manifest_path")
    return parts


def _checked_path(root: Path, parts: tuple[str, ...]) -> Path:
    """Refuse links/reparse points at every descendant, including missing targets."""
    candidate = root
    for position, component in enumerate(parts):
        candidate = candidate / component
        info = candidate.lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            or candidate.resolve() != candidate
        ):
            raise ValueError("linked_path")
        if position < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise ValueError("not_a_directory")
        if position == len(parts) - 1 and not stat.S_ISREG(info.st_mode):
            raise ValueError("not_a_regular_file")
    return candidate


def _pairs_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_manifest_key")
        result[key] = value
    return result


def _load_manifest(source: Path) -> dict[str, tuple[tuple[str, ...], str]]:
    manifest = _checked_path(source, ("manifest.json",))
    with manifest.open("rb") as handle:
        raw = handle.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("manifest_too_large")
    data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs_without_duplicates)
    if (
        not isinstance(data, dict) or set(data) != {"version", "files"}
        or not isinstance(data["version"], str) or not data["version"].strip()
        or len(data["version"]) > 128
        or not isinstance(data["files"], dict) or not data["files"]
    ):
        raise ValueError("invalid_manifest_schema")
    entries, casefolded = {}, set()
    for relative, digest in data["files"].items():
        parts = _manifest_parts(relative)
        if relative.casefold() in casefolded or not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise ValueError("invalid_manifest_entry")
        casefolded.add(relative.casefold())
        entries[relative] = (parts, digest.lower())
    return entries


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(profiles_root: Path, source: Path) -> tuple[int, list[dict]]:
    """Check the source first; an invalid source must not be used as a baseline."""
    try:
        source = Path(source).resolve()
        entries = _load_manifest(source)
    except (OSError, ValueError, TypeError, RuntimeError, RecursionError):
        return 2, [_source_error()]

    findings = []
    for relative, (parts, expected) in sorted(entries.items()):
        try:
            valid = _sha256(_checked_path(source, parts)) == expected
        except (OSError, ValueError, RuntimeError):
            valid = False
        if not valid:
            findings.append(_source_error(relative))
    if findings:
        return 2, findings

    try:
        profiles_root = Path(profiles_root).resolve()
    except (OSError, ValueError, TypeError, RuntimeError):
        return 2, [_source_error()]
    unsafe = False
    for profile in PROFILES:
        for relative, (parts, expected) in sorted(entries.items()):
            try:
                valid = _sha256(_checked_path(profiles_root, (profile, *parts))) == expected
            except FileNotFoundError:
                findings.append(_finding(profile, relative, "missing"))
                continue
            except (OSError, ValueError, RuntimeError):
                unsafe = True
                valid = False
            if not valid:
                findings.append(_finding(profile, relative, "modified"))
    return (2 if unsafe else 1 if findings else 0), findings


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default error includes user input; keep it out of the report.
        raise ValueError("invalid_arguments")


def main(argv=None) -> int:
    parser = _Parser(description="Report integrity drift in six DFIR skill copies; never repairs files.")
    parser.add_argument("--profiles-root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True, help="Version directory containing manifest.json.")
    try:
        args = parser.parse_args(argv)
        rc, findings = check(args.profiles_root, args.source)
    except Exception:
        # Do not expose parser excerpts, OS paths, contents or digests in exceptions.
        rc, findings = 2, [_source_error()]
    print(json.dumps({"status": {0: "ok", 1: "drift", 2: "error"}[rc], "findings": findings}, ensure_ascii=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
