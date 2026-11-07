---
name: digital-forensics
description: "Use when triaging files and preserving evidence."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [forensics, file-triage, magic-bytes, evidence, integrity]
---

# Digital Forensics

Use this skill for authorized local evidence, CTF samples, incident artifacts, and unknown-file triage. The default posture is **read-only, scope-limited, evidence-driven, and reproducible**.

## When to Use

Load this skill when the user asks to identify unknown or misleadingly named files, preserve and verify local evidence, compare file-classification tools, inspect Magic Bytes, validate container/document/executable structure, or produce a reproducible file-triage report. It also applies when an exact forensic utility must be provisioned and its output distinguished from a substitute.

Do not use it to execute samples, develop exploits, or expand beyond the explicitly authorized evidence scope.

## 结论收口

下结论前读 `references/evidence-record.md`。解题答案不写等级词。没有当次回执的句子写“未取到”，不要写成不存在。

## Non-negotiable boundaries

1. Confirm the authorized files or directory before examining anything.
2. Do not scan unrelated locations.
3. Do not execute samples, enable macros, mount untrusted images read-write, or extract archives over originals.
4. Keep original evidence read-only. Put scripts under a separate `scripts/` area and outputs/copies under a separate `work/` area.
5. Record SHA-256 before analysis and verify it again afterward when integrity matters.
6. Hash values must be copied **VERBATIM from live command output**. Never "complete" an observed 8-char prefix into a 64-char hash by padding or recalling the tail from memory — a hash whose suffix you did not observe is fabricated evidence, and it will fail a re-verification. Cross-verify critical hashes from a second independent source (supplied SHA256SUMS manifest + an independent recompute, e.g. hashing each member of the outer archive separately) and confirm sizes with `Get-Item`/`wc -c` at the same time. Where only a prefix was verified, say so explicitly.
7. Treat names and extensions as untrusted labels, not evidence.
7. User-space read-only commands may still update filesystem access timestamps (for example, NTFS AccessTime). When timestamp preservation matters, analyze a snapshot/image with no-atime semantics or record filesystem metadata before and after. Never write an old access time back to the original merely to hide the side effect.

## Unknown-file triage workflow

### 1. State the frame before conclusions

Record:

- known information;
- unknown information;
- exact analysis scope;
- planned read-only tools and outputs.

Do not announce a file type before collecting evidence.

### 2. Inventory and pre-hash

Enumerate only the authorized samples. Record original name, extension, byte size, path, and SHA-256. Save command output outside the evidence directory.

### 3. Verify the actual tool environment

Identify the real OS, shell, tool paths, and versions. Distinguish Git Bash/MSYS2/WSL/PowerShell/CMD instead of inferring from drive-letter paths.

For requested tools, verify direct invocation in the **same shell used for analysis**. If an exact tool is missing:

- report the missing tool honestly;
- label any read-only substitute as incomplete coverage;
- never present substitute output as the requested tool's output;
- when authorized to install, use an OS-trusted package manager or the tool's official release, verify path/version/checksum, then repeat the analysis with the original tool.

### 4. Collect independent evidence

Use multiple read-only evidence classes:

- `file` or another independent classifier;
- `xxd`/hex view of the header and, when useful, trailer or key offsets;
- GNU `strings` with offsets;
- ExifTool metadata and format output;
- format-specific structural validation.

`strings` and metadata are supporting evidence. A single readable phrase, extension, metadata field, or classifier result is never sufficient by itself.

### 5. Validate structure at the claimed format's granularity

Map the raw structure **before** invoking a specialist validator or decoder. Record offsets, declared lengths, data/reference ranges, terminal structures, and checksum inputs. A file opening successfully is corroboration, not proof that ordering, CRCs, references, or EOF conditions are valid; a decoder failure does not identify the cause.

Examples:

- ZIP: local header, central directory, EOCD, offsets and entry counts;
- PNG: signature, chunk sequence, CRCs, IHDR, IDAT/IEND consistency;
- PE: `MZ`, `e_lfanew`, `PE\0\0`, COFF/optional header, section bounds, entry point;
- PDF: header, objects, XRef, trailer, `startxref`, EOF;
- SQLite: 16-byte header, page size/count, schema, read-only integrity check;
- PCAP: byte order, timestamp resolution, version, snap length, 32-bit link type, record lengths;
- JPEG: SOI, APP/JFIF/Exif, SOF, SOS, EOI.

For every anomaly separate:

1. **Observation** — directly observed bytes, offsets, lengths, references, or checksum comparison;
2. **Inference** — the narrow interpretation supported by those facts;
3. **Alternative Explanations** — other causes still compatible with the evidence;
4. **Conclusion** — the narrowest defensible status;
5. **Next Validation** — what evidence would distinguish the alternatives.

A checksum mismatch proves only that the stored value and the checksum of the current covered bytes differ. A missing terminal structure proves absence/incompleteness, not why it is absent. Keep the conclusion no more specific than the verified structure supports.

### 6. Resolve conflicts instead of voting

When tools disagree:

1. Preserve each exact output and exit code.
2. Separate a parser warning, unsupported-format error, and true contradictory value.
3. Re-read the raw bytes at the documented field offset and width.
4. Compare against the format specification or installed parser source when necessary.
5. Explain why one result is authoritative for that field.
6. Retain unaffected higher-level conclusions when only a subtype field conflicts.

A parser error on an unsupported format is a coverage gap, not evidence that the file is not that format.

### 7. Post-verify integrity

Recompute SHA-256, compare the before/after manifests mechanically, and confirm no analysis files appeared inside the evidence directory. A successful read-only workflow reports both content integrity and any tool failures encountered.

## Reporting contract

For every file include:

- original filename, path, extension, byte size, SHA-256;
- Magic Bytes with offsets and their format meaning;
- exact `file` result;
- GNU `strings` command and type-relevant lines;
- ExifTool command and type-relevant output, including warnings/errors;
- structural checks performed;
- observation, inference, and conclusion as distinct statements;
- actual type and whether the extension matches;
- conflicts, limitations, and their resolution.

End with a concise all-file table, unresolved issues, tool provenance, and before/after integrity status. Do not repeat large raw outputs in the report body; preserve them separately.

## Supporting material

- See `references/unknown-file-triage.md` for Windows/Git Bash provisioning, safe offset handling, and concrete parser-conflict diagnostics.
- See `references/windows-portable-validator-provisioning.md` for official portable-asset verification, process-local PowerShell/Git Bash activation, specialist-validator capture, and mechanical acceptance gates.
- See `references/file-structure-validation.md` for manual-first PNG/JPEG/ZIP/PDF parsing, checksum discipline, and anomaly reasoning boundaries.
- See `references/docx-version-diff-rebaseline.md` for diffing two versions of the same DOCX/OOXML file: editor-resave fingerprint noise (shading/rFonts/numId/bookmarks/app.xml stats), the drift-detection and delta-rebaseline protocol (anchor double-check, lock-file gate, precise updates with assert-once, archive-old-data), efficient subtree-hash diffing of huge XML, the CRLF false-mismatch trap, and concurrent-writer/parallel-session merge discipline.
- See `templates/file-triage-report.md` for a reusable evidence report skeleton.

## Verification checklist

- [ ] Scope contains only authorized samples.
- [ ] Originals were not executed, renamed, overwritten, or extracted over.
- [ ] Pre-analysis SHA-256 exists for every sample.
- [ ] Requested tools were actually invoked and version-checked.
- [ ] Every conclusion has Magic Bytes or structural support plus independent corroboration.
- [ ] Warnings, non-zero exits, unsupported formats, and subtype conflicts are explicit.
- [ ] Post-analysis SHA-256 matches mechanically.
- [ ] Outputs are outside the evidence directory.
