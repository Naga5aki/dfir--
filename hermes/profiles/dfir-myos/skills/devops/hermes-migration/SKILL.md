---
name: hermes-migration
description: "Use when moving Hermes + SecurityLab to a new Windows PC."
version: 1.0.0
author: SecurityLab
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, migration, backup, restore, mcp, securitylab, windows]
---

# Hermes Migration (Windows)

## When to Use

Use when the user is moving an existing Hermes install (config, skills, memory, sessions, projects, MCP servers) from one Windows laptop to another, especially when the SecurityLab CTF workspace must remain usable.

Use this skill when the user moves Hermes + SecurityLab (or a similar Hermes profile) to a new Windows laptop. The authoritative runbook is `D:\Hermes\SecurityLab\migration\README.md`; the measured baseline is `INVENTORY.md`. Read both before acting.

## Non-negotiables

1. **Quit Hermes before restore/import.** `hermes import` writes `state.db`; a live desktop app can hold it. Run restore from a normal PowerShell/CMD, not from inside a Hermes session.
2. **Never copy venvs.** `tools\venv-ctf` and `mem-forensics-mcp\.venv` contain absolute paths. Recreate with `uv`.
3. **MYOS is not portable.** Reinstall the app (service/DBus/PostgreSQL/license); migrate only `D:\MYOS\Case`.
4. **The package contains secrets.** `hermes-backup.zip` includes `.env`, `auth.json`, `state.db`; `secrets\HKCU-Environment.reg` includes API keys. Keep the package on an encrypted disk; never upload it.
5. **Prefer the same drive letters** (`D:\Hermes`, `D:\CTF_Misc_Tools`, `D:\MYOS`). Different user/drive is supported only via `relocate_paths.py`.

## Phase commands

Old machine (export; can run live):

```powershell
cd D:\Hermes\SecurityLab\migration
python scripts\export_old.py --destination E:\HermesMigration\2026-10-18 --profile full --include-wsl --force
```

Profiles: `core` (~8 GB: Hermes + projects), `mcp` (~18 GB: + MCP tool subtrees), `full` (~120 GB: + all `D:\CTF_Misc_Tools` + `D:\MYOS\Case`).

New machine, after installing Hermes but **before opening the desktop app**:

```powershell
E:\HermesMigration\2026-10-18\run.cmd scripts\preflight_new.py --package E:\HermesMigration\2026-10-18
E:\HermesMigration\2026-10-18\run.cmd scripts\restore_new.py --package E:\HermesMigration\2026-10-18 --old-user 23037
```

Then open Hermes and verify:

```powershell
D:\Hermes\SecurityLab\migration\run.cmd scripts\verify_migration.py --package E:\HermesMigration\2026-10-18 --target-root D:\Hermes
```

## Acceptance criteria

- `project-SecurityLab` manifest: 0 missing, 0 size mismatch, 0 hash mismatch.
- `hermes mcp list` shows 15 servers; `hermes project list` shows `攻防取证助手` / SecurityLab.
- 12 `SKILL.md` under `.hermes\skills\security`.
- `securitylab_retrieve.py search --query "内存取证入口"` exits 0 with `status=covered`.
- `securitylab_doctor.py --checks broken_links,schema_drift` exits 0.
- `venv-ctf` imports `z3,sympy,gmpy2,lief,keystone,websockets`.
- Per-MCP real call: IDA 13337, jadx 8650, MYOS DBus health, CTF-Misc-Arsenal hook, memforensics status.

## Manual gates (do not fake)

- MYOS installer + license; restore `Case` after install.
- IDA Pro licensing/installation; open IDA once so `idapythonrc.py` starts the plugin.
- jadx GUI plugin jar at `%APPDATA%\skylot\jadx\config\plugins\dropins\jadx-ai-mcp-6.4.1.jar`.
- Docker Desktop + `docker mcp` profile `security_lab`.
- WSL import: `wsl --import Ubuntu C:\WSL\Ubuntu <package>\wsl\ubuntu.tar --version 2`.

## Known pitfalls

- `state.db` is version-sensitive: restore with the same Hermes version first, then update.
- `projects.db` may list dead paths (`D:\CTF-Script-Assistant`, `D:\Misc学习`); report them, do not invent directories.
- Hook approvals are mtime-based: after relocation run `hermes hooks doctor` and re-approve if needed.
- `hermes doctor` exit 1 often means optional API keys are missing; only exit >=2 is a hard config failure.
- Session `cwd` fields may still point at old paths; new sessions are fine.

## Reporting

Use Observation / Inference / Conclusion. Never claim a phase passed without the command output; record exact counts and failures in `migration\logs\`.
