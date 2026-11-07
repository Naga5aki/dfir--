#!/usr/bin/env python3
"""Capture a case-local lesson without auto-editing global memory/skills.

Promotion is deliberately manual: one case can produce noise. Promote only a
rule that is verified on a second case, and never store answer values, keys,
tokens, credentials or raw evidence in a lesson.
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

CATEGORIES = {
    "tool-gap",
    "evidence-pattern",
    "prompt-rule",
    "skill-rule",
    "false-stop",
    "noise",
    "wrong-route",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Append a case-local DFIR lesson")
    ap.add_argument("--notes", required=True, help="case notes directory")
    ap.add_argument("--category", required=True, choices=sorted(CATEGORIES))
    ap.add_argument("--lesson", required=True, help="generalizable lesson, no answer values")
    ap.add_argument("--evidence", default="", help="path/field or tool output location, not a secret value")
    ap.add_argument("--next", dest="next_step", default="", help="one concrete next step")
    args = ap.parse_args()
    notes = Path(args.notes)
    notes.mkdir(parents=True, exist_ok=True)
    text = "\n".join([args.lesson, args.evidence, args.next_step])
    if re.search(r"(?i)(password|passwd|token|secret|api[_-]?key)\s*[:=]\s*\S+", text):
        print("refusing to store what looks like a credential; record only field/path names", flush=True)
        return 2
    path = notes / "lessons.md"
    block = (
        f"\n## {datetime.now():%Y-%m-%d %H:%M} | {args.category}\n"
        f"- 教训：{args.lesson.strip()}\n"
        f"- 证据位置：{args.evidence.strip() or '未记录'}\n"
        f"- 下一步：{args.next_step.strip() or '未记录'}\n"
        f"- 状态：case-local（未提升到 skill/memory）\n"
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(block)
    print(f"appended {path}")
    print("promotion rule: repeat on a second case -> move a general rule to SKILL.md; never store answers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
