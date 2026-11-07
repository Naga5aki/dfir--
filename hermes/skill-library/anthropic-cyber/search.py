#!/usr/bin/env python3
"""Search the local Anthropic Cybersecurity Skills library."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.json"


def tokens(text):
    return re.findall(r"[a-z0-9][a-z0-9_.+-]{1,}", text.lower())


def search(query, limit=8, domain=""):
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    skills = data.get("skills", [])
    qtokens = tokens(query)
    phrase = query.lower()
    scored = []
    for skill in skills:
        name = skill.get("name", "")
        desc = skill.get("description", "")
        haystack = f"{name} {desc} {skill.get('subdomain', '')}".lower()
        if domain and domain not in haystack:
            continue
        score = 0
        for token in qtokens:
            score += name.lower().count(token) * 4
            score += haystack.count(token)
        if phrase in haystack:
            score += 10
        if score:
            scored.append((score, skill))
    scored.sort(key=lambda item: (-item[0], item[1].get("name", "")))
    return scored[:limit]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("usage: search.py <query> [--limit N] [--domain NAME]")
        return 0

    limit = 8
    domain = ""
    query_parts = []
    i = 0
    while i < len(args):
        if args[i] in ("--limit", "-n") and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif args[i] == "--domain" and i + 1 < len(args):
            domain = args[i + 1].lower()
            i += 2
        else:
            query_parts.append(args[i])
            i += 1

    query = " ".join(query_parts).strip()
    if not query:
        data = json.loads(INDEX.read_text(encoding="utf-8"))
        skills = data.get("skills", [])
        from collections import Counter
        counts = Counter(s.get("domain", "?") for s in skills)
        for name, count in counts.most_common():
            print(f"{name}: {count}")
        return 0

    results = search(query, limit, domain)
    if not results:
        print(f"No match for: {query}")
        return 0

    for score, skill in results:
        rel = Path(skill.get("path", "")) / "SKILL.md"
        print(f"[{score}] {skill.get('name', '')}")
        print(f"    rel: {rel}")
        print(f"    desc: {skill.get('description', '')[:240]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
