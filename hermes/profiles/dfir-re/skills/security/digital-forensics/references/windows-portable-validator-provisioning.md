# Windows portable validator provisioning

Use this reference when an authorized forensic workflow needs project-local Windows validators without a permanent install or PATH change. It covers provenance, extraction, shell activation, read-only validation, and acceptance checks. Resolve all versions and paths at run time; never copy the examples as frozen environment facts.

## 1. Canonical evidence path before tooling

1. Define the authorized source and canonical evidence target.
2. Hash the authorized files before any layout change.
3. If the canonical target already exists, compare every expected filename and SHA-256 before writing anything. Matching files should be reused; mismatches must stop the copy instead of being overwritten.
4. If the original source is already absent at preflight, record that as a pre-existing provenance gap. Do not reconstruct it from analysis output. Continue only when the canonical copy is independently authorized and mechanically matches a trusted manifest.
5. Keep downloads and validation output outside evidence. Re-enumerate evidence after the work.

## 2. Select and verify official portable assets

Use only the project website, official repository, official release page, or an OS-trusted package manager allowed by the user.

For each download record:

- official release page and exact asset URL;
- release/tag and asset filename;
- byte size and archive SHA-256;
- official checksum, release-API asset digest, signature, or attestation when available;
- extraction root;
- executable path, byte size, SHA-256, and runtime version.

Verification order:

1. Download over HTTPS to the authorized project downloads directory.
2. Compute the archive SHA-256 locally.
3. Compare it with an official checksum or machine-readable release digest before extraction.
4. Test/list the archive before extracting. Probe an already available trusted extractor first; if it can list and extract the format successfully, do not add another unapproved dependency.
5. Refuse a pre-existing non-empty install target unless its contents have been separately verified.
6. After extraction, invoke the executable by absolute path and record its version and hash.
7. Treat Authenticode or Sigstore as additional provenance evidence. An unsigned executable is not by itself proof of an unofficial package when the enclosing official archive was independently checksum-verified; report the layers separately. Never claim a signature was verified when no suitable verifier actually ran.

## 3. Process-local activation files

Create separate PowerShell and Git Bash activation files. Both should:

- verify every directory exists before changing PATH;
- affect only the current process;
- be idempotent when loaded twice;
- place narrowly scoped project tool directories before the inherited PATH;
- place broad toolchain directories after the inherited PATH to reduce command shadowing;
- refresh command lookup (`hash -r` in Bash).

### PowerShell

Use Windows paths and assign only `$env:PATH`. Dot-source the file in a new `powershell.exe -NoProfile` process. Verify each bare command with `Get-Command`, run its version command, and count each inserted directory after loading twice.

### Git Bash

Git Bash PATH is colon-delimited. Convert drive-letter directories to MSYS form before insertion:

- `D:\Tools\bin` → `/d/Tools/bin`
- `C:\Users\name\bin` → `/c/Users/name/bin`

A drive-letter form such as `D:/Tools/bin` can pass `test -d` yet break when inserted into PATH because the drive colon becomes a separator. Verify PATH structure with Bash built-ins. Do not delegate this check to a native Windows Python process: MSYS may convert PATH to Windows form at the process boundary, producing a false test result.

### Isolation verification

Run each activation file in a fresh child shell, capture stdout/stderr/exit status, and verify:

- every bare command resolves to the intended executable;
- every version command succeeds;
- loading twice leaves one copy of each added directory;
- the parent shell still lacks the new entries after the child exits.

When embedding PowerShell in a Bash command, prevent Bash from expanding PowerShell `$variables`; prefer a `.ps1` file or a single-quoted PowerShell command string.

## 4. Read-only specialist validation

Before specialist tools run, save a fresh evidence SHA-256 manifest. For every validator invocation preserve separately:

- exact input path and input SHA-256;
- actual executable path and version;
- stdout;
- stderr;
- exit status.

Read exit semantics from the installed tool's own help or official manual. Separate shell invocation failure from a validator-reported file error. A decoder that tolerates and reads a malformed file does not erase a raw structural defect; a decoder failure does not identify the cause.

For image tools, use identify/check modes that do not write an output image. Point temporary storage to work when supported and verify no residual files remain. For document validators, avoid repair, rewrite, linearize, decrypt, or output-generation flags.

## 5. Conflict localization order

When specialist output differs from prior structural analysis:

1. Reconfirm the exact input path and SHA-256.
2. Reconfirm the resolved executable path and version.
3. Separate stdout, stderr, and exit status.
4. Determine whether the tool used tolerant parsing, metadata-only parsing, or complete decoding.
5. Return to documented raw offsets, lengths, references, and checksum coverage.
6. State which evidence is authoritative for the disputed field and retain unaffected conclusions.

Different coverage is not automatically a contradiction. For example, one metadata parser may omit CRC validation while a decoder reports it; the independently recomputed CRC remains the direct evidence.

## 6. Post-validation acceptance gate

Before declaring completion:

- recompute every evidence SHA-256;
- compare pre/post manifests mechanically;
- confirm the evidence file set is unchanged;
- verify archive and executable hashes again;
- verify expected validator exit statuses and empty/non-empty stderr conditions;
- re-run fresh-shell activation tests;
- verify report sections and Memory/project-record updates when required.

A small deterministic acceptance script is preferable to checking these items by eye. It must be read-only and must fail non-zero on any unmet condition.

## Durable pitfalls

- A directory path that works as a command argument may still be invalid as a POSIX PATH entry.
- A validator's non-zero exit can be a useful file result; do not hide it with `set -e` before capturing stderr and status.
- A failed wrapper or quoting probe is not a file-validation result. Fix the invocation layer and rerun the exact probe.
- Do not install an extra archive tool merely because the familiar command is absent; first test available trusted extractors against the actual archive.
- Never convert a successful decoder run into a claim of structural completeness, or a checksum mismatch into a claim about which field changed.
