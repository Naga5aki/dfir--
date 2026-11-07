---
name: project-skill-maintenance
description: Audit and maintain repository-local agent skills.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, project-context, maintenance, collaboration, git]
    related_skills: [hermes-agent-skill-authoring]
---

# Project Skill Maintenance

Audit and improve skills stored inside a project repository without confusing them with profile-local or bundled skills. Treat activation, content quality, project ownership, and Git safety as separate verification dimensions.

## When to Use

Use this skill when asked to:

- inspect or improve `.hermes/skills/` or `.agents/skills/`;
- assess whether project skills cover a repository's workflows;
- reconcile project documentation with the actual skill inventory;
- add project maintenance, collaboration, or knowledge-management rules;
- determine why repository-local skills are not available in a session;
- review an external skill package for adoption into the repository before any file enters an active skills path (safe extraction, hashed inventory, disposition plan — see `references/external-skill-package-review.md`).

Do not use it for authoring skills shipped inside the Hermes Agent source repository; use `hermes-agent-skill-authoring` for that case.

## Prerequisites

Before changing anything:

1. Read the repository's active context file, especially `AGENTS.md`, `.hermes.md`, or `HERMES.md`.
2. Inspect the current working directory, Git root, branch, worktree status, and branch divergence.
3. Identify files owned or actively maintained by other agents.
4. Inventory repository-local skills separately from profile-local, bundled, hub-installed, external, and pinned skills.
5. Confirm whether the user requested analysis only or authorized edits.

If the user requested analysis only, stop after the report. Do not treat a later recommendation as permission to edit.

## Procedure

### 1. Establish project truth

Read the root README, agent instructions, collaboration documentation, project skill files, and only the application structure needed to understand integration boundaries. Verify statements against Git and the filesystem rather than trusting a documentation list.

For a request to improve the workbench itself, audit structure, knowledge ownership, project versus global Memory, skill routing, decision records, retrieval, and tool/validation contracts. Deliver system changes with evidence, dependencies, acceptance tests, and adoption gates; do not substitute challenge practice, a training timetable, or tool-install counts for system improvement. Evaluate external resources against a demonstrated gap and existing capabilities before recommending adoption.

Completion criterion: the report distinguishes observed repository state from intended architecture and addresses the requested system layer.

### 2. Separate inventory from activation

Record:

- skill directories actually present in the repository;
- skills named only in documentation;
- same-named skills installed in the active Hermes profile;
- whether repository-local skill trust is required;
- whether the current session actually exposes the project skills.

Use Hermes CLI help or current official documentation for trust and loading semantics. Do not mutate project trust merely to complete an audit; trust changes require explicit authorization.

Completion criterion: every claimed skill is classified by source and current availability.

### 3. Audit content quality

For each project skill, assess:

- trigger clarity and counter-triggers;
- required frontmatter and platform claims;
- actionable numbered steps with completion criteria;
- project architecture and ownership boundaries;
- evidence preservation, safety, and failure honesty;
- testing, diff review, and reporting requirements;
- malformed Markdown, encoding damage, and stale paths;
- overlap with another skill or project context file.

Keep project hard rules in the context file. Skills should encode repeatable task procedures rather than duplicate the entire context file.

Completion criterion: each skill has concrete strengths, gaps, and a recommended disposition.

### 4. Check multi-agent ownership

Before proposing edits, compare the planned files with other agents' active scopes and unique branch changes. Prefer skills and documentation when application code belongs to another agent. Never infer that a clean local worktree means another worktree is inactive.

Give independent reviewers read access to the approved plan, scope manifest, relevant baselines, staged changes, and validation artifacts; separate read permission from write ownership. A non-modifiable contract is still required evidence for authorization mapping. Bound the review to specific acceptance questions and reserve enough tool budget to persist its verdict rather than repeatedly commissioning broad audits.

Completion criterion: the proposal names the primary modifier, excludes overlapping writes, and supplies reviewers with the primary evidence needed for their verdict.

### 5. Design class-level updates

Prefer, in order:

1. patch an existing project skill;
2. add a concise `references/` file beneath an existing umbrella;
3. create a class-level maintenance skill only when no umbrella fits.

Avoid router-only skills, one-session names, branch-number names, and duplicated local/profile skills. If a profile-local and project-local skill would share a name, verify precedence before creating the duplicate.

Completion criterion: every new rule has one durable home and no unexplained overlap.

### 6. Declare scope before writing

Before any edit, state:

- exact files to be modified or created;
- reason for each file;
- expected behavioral impact;
- explicitly excluded code and directories.

Re-check Git status immediately before the first write. Distinguish the approved baseline and known existing changes from unexpected edits; pause on unaccounted target drift, stale branches, or overlapping ownership rather than treating every known untracked file as a new blocker. If the repository has no commits, use verified per-file backups and manifests for recovery; do not claim that Git can restore an unborn baseline.

Completion criterion: the user can review the full write scope before side effects occur.

### 7. Apply and verify

Modify only approved skill and documentation files. Validate frontmatter, encoding, links, related skill names, and platform declarations. For authority/routing changes, parse explicit ownership and forwarding records and exercise duplicate owners, conflicting routes, cycles, and dangling targets; counting labels or matching reassuring prose is not validation. State which graph was checked and keep unresolved historical or deep-reference conflicts visible.

For staging tests, record the command, working directory, resolved test root, test-source hash, and staged-to-sandbox file bindings. Preserve RED/GREEN logs and the reviewed diff, compare installed bytes to the reviewed revision, then run the relevant tests at the installed path; a green summary alone does not identify its test target. Compare protected historical sections byte-for-byte, preserving newline encoding, instead of claiming preservation from a visual diff alone.

Review `git diff` and `git status`; use the approved before-manifest when files are untracked and ordinary diffs cannot show their edits. Run project-specific skill validation if available. Start a fresh session when needed to verify project-skill discovery, because the current session may cache its skill index.

Completion criterion: the diff contains only approved files; staged, installed, and fresh-session verification are reported separately.

## Knowledge Management Rules

- Put stable, reusable procedures in `SKILL.md`.
- Put project-specific architecture and audit details in `references/`.
- Put reproducible starter artifacts in `templates/`.
- Put deterministic checks in `scripts/`.
- Do not store transient commit IDs, branch-ahead counts, task progress, credentials, challenge flags, or private samples.
- Mark project-specific observations that can drift with an explicit revalidation step.

## Pitfalls

1. Documentation naming a skill does not prove the file exists.
2. A valid `SKILL.md` does not prove the current session loaded it.
3. `hermes skills list` and repository inventory answer different questions; report the source of each result.
4. Do not run a trust command during a read-only audit.
5. Do not copy a mature profile-local skill into the repository before checking name precedence and ownership.
6. Do not update application code merely because integration documentation is incomplete.
7. Do not encode temporary branch divergence or setup failures as permanent rules.
8. Do not normalize unrelated documentation while making a focused skill change.

## Verification Checklist

- [ ] Repository, branch, worktree, and status verified.
- [ ] Analysis-only versus edit authorization confirmed.
- [ ] Repository-local and profile-local skills inventoried separately.
- [ ] Current-session activation checked independently of file validity.
- [ ] Other-agent ownership and branch overlap reviewed.
- [ ] Exact files, reasons, impact, and exclusions stated before writing.
- [ ] Skill structure, encoding, and references validated.
- [ ] Final diff contains no application or unrelated changes.
- [ ] Fresh-session loading verification performed or explicitly left pending.

## Project References

- See `references/ctf-script-assistant.md` for the CTF-Script-Assistant ownership model, architecture, and project-skill audit baseline.
- See `references/external-skill-package-review.md` for the pre-adoption review of an external skill package: safe-extraction gate, one-pass hash inventory, fence-aware structural checks, harness-fit translation, and the change-list + single-report deliverable shape.
