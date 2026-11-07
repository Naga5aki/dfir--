# CTF-Script-Assistant Project Reference

This reference captures project-specific context for applying the `project-skill-maintenance` workflow. Revalidate it against the repository before every maintenance pass; Git and the current files remain authoritative.

## Project Purpose

CTF-Script-Assistant is a monorepo for CTF Misc scripts, digital-forensics utilities, reusable analysis libraries, Nagasaki Misc World, tests, documentation, and technical knowledge.

The intended dependency direction is:

```text
research or challenge prototype
→ reusable core algorithm/API
→ standalone script or CLI
→ GUI adapter
→ GUI presentation
```

Reusable algorithms should move gradually toward `packages/ctf_core`. GUI-specific code and PySide6 dependencies remain under `apps/nagasaki-misc-world`.

## Multi-Agent Ownership

Default work division:

- **Hermes:** CTF/Misc analysis, digital forensics, algorithm research, prototypes, independent review, documentation, and knowledge management.
- **Codex:** shared core APIs, engineering implementation, large refactors, cross-module tests, and legacy extraction.
- **Cursor:** Nagasaki Misc World, PySide6, GUI adapters, GUI plugins, and interactive UI debugging.
- **main worktree:** review, integration tests, merges, conflict resolution, and stable history.

Use one primary modifier per task. Other agents may research or review, but should not modify the same files concurrently without explicit coordination.

## Stable Repository Boundaries

Before a Hermes maintenance change:

1. Read `README.md`, `AGENTS.md`, and `docs/AI_COLLABORATION.md`.
2. Inspect `.hermes/skills/` and compare it with every skill named in documentation.
3. Inspect `apps/nagasaki-misc-world` only far enough to keep integration guidance accurate.
4. Do not modify GUI or application code when the task is limited to skills and documentation.
5. Treat `apps/nagasaki-misc-world/projects/` as legacy behavior that requires tests before extraction or removal.
6. Keep challenge inputs, outputs, virtual environments, caches, secrets, and private samples out of Git.

## Skill Audit Baseline

The reviewed repository state contained these project-local skill files:

- `ctf-misc-analysis`
- `ctf-script-development`
- `nagasaki-integration`

Project collaboration documentation also named `digital-forensics`, while the reviewed copy existed in the active Hermes profile rather than under the repository's `.hermes/skills/` directory. Recheck both locations before acting; do not assume this remains true.

The audit also found that repository-local skills and profile-local installed skills must be reported separately. Hermes CLI documents an explicit trust step for loading repo-local `./.hermes/skills` or `./.agents/skills`; do not change trust during an analysis-only pass.

## Project Skill Priorities

### CTF Misc analysis

Expected coverage includes evidence preservation, file-type skepticism, bounded hypothesis testing, reproducible transformations, candidate validation, explicit uncertainty, and knowledge capture.

### Python and CLI development

Expected coverage includes input/output separation, non-destructive defaults, explicit errors, deterministic behavior, reusable functions, dependency discipline, smallest-useful tests, diff review, and actual test reporting.

### Nagasaki integration

Expected coverage includes stable-core-first integration, `argparse` as an interface contract where applicable, GUI-neutral command construction, data-only external tool adapters, no reusable algorithms in event handlers, and Cursor ownership of GUI implementation by default.

### Project maintenance

Expected coverage includes worktree/branch preflight, synchronization checks, single-primary-modifier ownership, declared edit scope, no automatic commits, conflict discipline, and fresh-session skill-loading verification.

## Revalidation Checklist

- [ ] Current branch and Git root match the intended Hermes worktree.
- [ ] Worktree is clean or unrelated changes are explicitly preserved.
- [ ] Branch divergence from `main` is current, not copied from an old report.
- [ ] Cursor and Codex unique changes do not overlap the proposed files.
- [ ] Actual project skill files match collaboration documentation.
- [ ] Profile-local skill names do not create unverified collisions.
- [ ] No GUI, Python, or launcher files enter a skills/docs-only diff.
