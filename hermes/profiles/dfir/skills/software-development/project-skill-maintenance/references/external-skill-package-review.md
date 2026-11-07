# External Skill Package Review (Pre-Adoption)

Use when a third-party agent-skill package (a zip or checkout of `SKILL.md` trees) is proposed for a repository and must be assessed before anything enters an active skill path. Phase-one deliverables are a single review report, a machine-readable change list, and an evidence directory; adoption itself happens only after an explicit gate.

## 1. Extract like untrusted input

- Work in a scratch/`work/` directory; never extract over originals or into an active skills path.
- Walk every archive member BEFORE extracting: reject absolute paths, `..` segments, backslash drive tricks, `:`/NUL in names, and symlink or special-mode entries (`external_attr >> 16`; allow only regular files and directories).
- Reject encrypted entries (general-purpose flag bit 0) and implausible compression ratios.
- Read members through the zip reader (this validates CRCs), re-hash each extracted file, and keep the untouched original plus a copy with before/after SHA-256; source hash must be unchanged after the round.

## 2. One authoritative inventory pass

- Produce one JSON inventory (path, size, sha256, line count) for every file; reviewers reuse it and re-hash every file they actually read (mismatch = stop).
- For each `SKILL.md`, capture frontmatter (name, description, platforms, tool grants) plus section headers — outline first, deep-read only what a disposition needs.
- Record coverage honestly per file: `deep` (read in full) vs `scan` (targeted). A scan never counts as a full read, and the completion claim says which was which.

## 3. Structural and fit checks

- Markdown links: extract fence-aware — skip fenced code blocks and inline-code spans, or the scan false-fires on code samples (`["cat /flag"](...)`, `$_GET[b]`, `{{bbox}}`). The claim it supports is "explicit markdown targets exist", not "anchors/links are valid".
- Pattern scans (install commands, network verbs, `eval`/`subprocess`) generate review leads only; a security/CTF package legitimately carries them as instruction text — classify per file, never report counts alone as findings.
- Client-fit: `allowed-tools` / `compatibility` fields naming another agent harness need a translation decision before adoption; keep each description's trigger AND negative triggers inside the host index's leading characters (Hermes derives the index line from ~60 chars, truncating with `...`), and verify the length programmatically.
- Same-name collisions with profile/global skills are decisions (merge / override / rename), not accidents — resolve and record precedence explicitly; the project tier outranks the profile tier where both load.

## 4. Plan deliverable

- `change-list.json`: per-module disposition (keep / extend / merge / new / verify-later) with exact target paths, gates, and an explicit do-not-touch list.
- One report: source record (hashes, license, read side effects), evidence index, integration-mode decision, per-module dispositions, risks, and the next phase's verification plan.
- Defer activation experiments (loading, trust, precedence) to the gated next phase; phase one writes only inside the isolated work directory.
- Bulk review delegations must use the incremental-write contract (one output artifact per reviewer, written as it goes) — see `gated-knowledge-promotion`, standing rule 6.

## Pitfalls

- Reviewing means reading: do not run the package's installers, scripts, or tests during review — they are read-only text until an approved phase executes them.
- A directory that merely looks like project skills proves nothing about loading; activation depends on the host harness's own trust/discovery gate (e.g. git-root detection plus a trust entry) — verify against the live harness, not the package's README.
- The original archive is evidence: hash before and after, and disclose read side effects (e.g. access-time updates) instead of hiding them.
