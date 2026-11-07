"""Read-only inventory of dfir profile MCP includes and enabled domain skills."""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

ROOT = Path(r"D:\ForensicsAgent\hermes\profiles")
PROFILES = ["dfir", "dfir-max", "dfir-mem", "dfir-myos", "dfir-pcap", "dfir-re"]
OUT = Path(r"D:\ForensicsAgent\_hexp_review_scripts\profile_inventory.txt")


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


lines: list[str] = []
for name in PROFILES:
    cfg = load(ROOT / name / "config.yaml")
    lines.append("=" * 72)
    lines.append(name)
    lines.append(f"memory_enabled={cfg.get('memory', {}).get('memory_enabled')}")
    lines.append(f"max_turns={cfg.get('agent', {}).get('max_turns')} budget={cfg.get('agent', {}).get('run_budget_seconds')}")
    lines.append(f"context={cfg.get('model', {}).get('context_length')} model={cfg.get('model', {}).get('default')}")
    servers = cfg.get("mcp_servers") or {}
    for srv, spec in servers.items():
        if not isinstance(spec, dict):
            lines.append(f"  mcp {srv}: {spec}")
            continue
        enabled = spec.get("enabled")
        url = spec.get("url")
        command = spec.get("command")
        tools = spec.get("tools") or {}
        include = tools.get("include") if isinstance(tools, dict) else None
        lines.append(f"  mcp {srv} enabled={enabled}")
        if url:
            lines.append(f"    url={url}")
        if command:
            lines.append(f"    command={command}")
        if include:
            lines.append("    include:")
            for item in include:
                lines.append(f"      - {item}")
        else:
            lines.append(f"    tools={tools}")
    disabled = set((cfg.get("skills") or {}).get("disabled") or [])
    lines.append(f"  disabled_count={len(disabled)}")
    domain = []
    for cat in ("security", "forensics"):
        base = ROOT / name / "skills" / cat
        if not base.exists():
            continue
        for skill in sorted(p for p in base.iterdir() if p.is_dir()):
            md = skill / "SKILL.md"
            if not md.exists():
                continue
            text = md.read_text(encoding="utf-8-sig")
            desc = ""
            if text.startswith("---"):
                end = text.find("\n---", 3)
                fm = text[3:end]
                for line in fm.splitlines():
                    if line.startswith("description:"):
                        desc = line.split(":", 1)[1].strip()
            state = "DISABLED" if skill.name in disabled else "enabled"
            domain.append((state, cat, skill.name, md.stat().st_size, desc[:120]))
    for state, cat, skill, size, desc in domain:
        lines.append(f"  [{state}] {cat}/{skill} {size}B | {desc}")

# hash compare key skills across profiles
lines.append("=" * 72)
lines.append("skill hash drift across profiles")
names = [
    "security/myos-results-analysis/SKILL.md",
    "security/memory-forensics-local/SKILL.md",
    "security/ida-reverse/SKILL.md",
    "security/wire-toutetu/SKILL.md",
    "security/digital-forensics/SKILL.md",
    "security/android-malware-analysis/SKILL.md",
    "forensics/android-app-forensics/SKILL.md",
    "forensics/linux-loader/SKILL.md",
    "forensics/windows-loader/SKILL.md",
]
for rel in names:
    hashes = {}
    for name in PROFILES:
        path = ROOT / name / "skills" / rel
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
            hashes.setdefault(digest, []).append(name)
        else:
            hashes.setdefault("MISSING", []).append(name)
    lines.append(f"{rel}: { {k: v for k, v in hashes.items()} }")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(OUT)
print("lines", len(lines))
