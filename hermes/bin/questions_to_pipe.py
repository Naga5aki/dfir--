#!/usr/bin/env python
"""Convert a pasted contest question list into `N|single-line` format.

Continuation lines (options, wrapped text) join the previous numbered item;
blank lines are dropped. If the text has no numbered lines at all, every
non-empty line becomes its own question.

usage: questions_to_pipe.py <infile> <outfile>
"""

import re
import sys
from pathlib import Path

NUMBERED = re.compile(r"^(\d+)\s*[.、．]\s*(.*)$")


def to_pipe_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    if not any(NUMBERED.match(line) for line in lines if line):
        items = [line for line in lines if line]
        return [f"{i}|{line}" for i, line in enumerate(items, 1)]
    out: list[str] = []
    for line in lines:
        if not line:
            continue
        match = NUMBERED.match(line)
        if match:
            out.append(f"{int(match.group(1))}|{match.group(2).strip()}")
        elif out:
            out[-1] = f"{out[-1]} {line}"
        # text before the first numbered line is a title; drop it
    return out


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: questions_to_pipe.py <infile> <outfile>", file=sys.stderr)
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    text = src.read_text(encoding="utf-8-sig", errors="replace")
    dst.write_text("\n".join(to_pipe_lines(text)) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
