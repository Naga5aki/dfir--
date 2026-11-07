# Unknown File Triage Report

## Scope and controls

- **Authorization/source:** <authorized local evidence, CTF, lab, etc.>
- **Evidence root:** `<path>`
- **Included samples:** <count/list>
- **Excluded scope:** <directories or systems not examined>
- **Read-only controls:** <how originals were protected>
- **Output directory:** `<path outside evidence>`

## Known / unknown / plan

### Known

- <fact provided by the user or inventory>

### Unknown

- <type, structure, provenance, etc.>

### Plan

1. Inventory and pre-hash.
2. Record tool paths and versions.
3. Run read-only classifiers, hex inspection, strings, and metadata tools.
4. Validate format structure.
5. Resolve conflicts.
6. Post-hash and compare.

## Tool provenance

| Tool | Absolute path | Version | Source | Limitations |
|---|---|---|---|---|
| `file` | `<path>` | `<version>` | `<source>` | `<none/notes>` |
| `xxd` | `<path>` | `<version>` | `<source>` | `<none/notes>` |
| GNU `strings` | `<path>` | `<version>` | `<source>` | `<none/notes>` |
| ExifTool | `<path>` | `<version>` | `<source>` | `<none/notes>` |

## Per-file findings

### `<original filename>`

- **Path:** `<original path>`
- **Original extension:** `<extension or none>`
- **Size:** `<bytes>`
- **Pre-analysis SHA-256:** `<hash>`
- **Magic Bytes:** `<offset: hex — meaning>`
- **`file` command/result:**
  - Command: `<exact command>`
  - Result: `<exact output>`
- **GNU `strings`:**
  - Command: `<exact command>`
  - Key lines: `<offset + relevant string, or none>`
- **ExifTool:**
  - Command: `<exact command>`
  - Exit status: `<status>`
  - Key output/warnings/errors: `<exact relevant lines>`
- **Structure validation:** `<checks and outcomes>`
- **Observation:** `<direct bytes/tool facts>`
- **Inference:** `<reasoned interpretation>`
- **Conclusion / actual type:** `<supported granularity>`
- **Extension match:** `matching / mismatching / unresolved`
- **Conflicts and resolution:** `<none, or exact disagreement and why resolved>`

<!-- Repeat the per-file block for every authorized sample. -->

## Summary

| File | Extension | Magic | `file` result | Actual type | Extension match | Primary evidence |
|---|---|---|---|---|---|---|
| `<name>` | `<ext>` | `<hex>` | `<result>` | `<type>` | `<status>` | `<basis>` |

## Integrity verification

| File | Before SHA-256 | After SHA-256 | Match |
|---|---|---|---|
| `<name>` | `<hash>` | `<hash>` | `OK/FAIL` |

- **Manifest comparison:** `<mechanical command and result>`
- **Evidence directory re-enumeration:** `<result>`
- **Originals executed/renamed/overwritten/extracted over:** `No / explain exception`

## Differences from prior analysis

- <conclusions changed or unchanged>
- <substitute evidence replaced by original-tool output>
- <new warnings, coverage gaps, or conflicts>

## Unresolved issues

- <issue and missing validation condition, or “None”>

## Raw-output locations

- `<path to file/xxd/strings/exiftool logs outside evidence>`
