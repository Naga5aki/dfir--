# DOCX Version Diff, Drift Detection, and Delta Rebaseline

Reference for the `digital-forensics` skill. Use when the same `.docx`
(or any OOXML file) exists in two versions and you must decide **what
actually changed** between them — source drift after an audit baseline,
"was the file re-edited?" questions, or verifying that a re-save only
made the changes its author claims.

## Editor-resave fingerprint (read this FIRST)

When a DOCX is opened in Word/WPS and re-saved, the XML is re-serialized.
The following differences are **serialization/format noise, not content
changes** — expect them in ANY before/after comparison of two saves by
the same or a different Office-family editor:

| Noise pattern | What it looks like | Verdict |
|---|---|---|
| Table shading/margins normalization | `w:shd` elements added/removed/merged across many tables; `w:tblCellMar` counts change | 149 of 172 tables differed in one real case; cell TEXT and structure (rows/cells/vMerge/gridSpan) were 0-diff |
| Run font normalization | `w:rFonts` rewritten (e.g. `ascii=仿宋` → `ascii="Times New Roman" eastAsia=仿宋 hAnsi=Times New Roman`) | formatting only |
| Font-size re-encode | `w:sz val="24"` → `val="21"` (half-points) | formatting only |
| Run splitting/merging | one text run split into two, `w:t xml:space="preserve"` added, bold prefix run extracted | compare concatenated text, not run count |
| Numbering re-reference | paragraph `numId 0` → `numId 138` (an existing bullet list) + `w:ind hanging` added; numbering.xml itself unchanged | 0 = "not in list"; the editor re-attached stray paragraphs to the real list. Text unchanged |
| `_GoBack` bookmark moves | bookmarkStart/End id=0 appears/disappears in one paragraph | editor artifact |
| `settings.xml` | `+<w:doNotDisplayPageBoundaries/>`, `+<w:rsid .../>` entries | serialization |
| `fontTable.xml` | entry order changes (e.g. Segoe UI Emoji block moves); font SET unchanged | serialization |
| `docProps/app.xml` | Words/Characters/TotalTime recomputed (one real case: 120,809 → 4,649 words) | metadata; app.xml stats were already known-unreliable (see docx-content-extraction.md) |
| `docProps/core.xml` | `<dcterms:modified>` timestamp advance | metadata |

**Consequence**: an element-level diff of two saves typically shows
dozens–hundreds of "differences" that are meaningless. Before declaring
real drift, compare at the SEMANTIC level: paragraph text sequence,
heading order/style/text, table cell text + structure, media parts,
relationship targets, styles.xml/numbering.xml bytes.

## Drift-handling protocol (baseline was already published)

When a task began with a published source anchor (size + full SHA-256)
and the source later changed:

1. **Recompute and compare**: size + SHA-256 vs the anchor. Changed →
   do NOT silently continue with either version.
2. **Characterize read-only before deciding**: full diff of old vs new
   (protocol below). One real case: only the 7,533rd non-empty paragraph
   differed (`CobalStrike` → `Cobalt Strike`) — a title typo fix that
   also advanced `docProps/core.xml modified`; all structure identical.
3. **Preserve every version's identity**: old copy stays as historical
   reference; an intermediate version observed only as hash/size is
   recorded as history, never used as a baseline.
4. **Rebaseline = precise updates only** (after the diff assertion
   passes): the extraction file gets the single expected string fix with
   an assert-once (`old string occurs exactly 1 time at the expected
   line`), plus a dated note at EOF saying the fix came from Source vN —
   never silently pretend the artifact was always correct. Old data JSONs
   are archived to a `v1-...-archive/` folder; current data is regenerated
   FROM the new OOXML (never hand-assembled hashes). Files whose content
   did not change keep their old hash and are NOT rewritten.
5. **End-of-round re-verification**: rerun the full phase acceptance
   checklist against the new anchor; confirm untouched files still carry
   their published hashes.

## Full version-diff protocol (v1 → v2)

Compare, read-only, at ALL of these levels and record each result with
its category (Content Change / Metadata Change / Container Serialization
Change / Relationship Change / Media Change / Unknown):

1. ZIP part set, part sizes, per-part SHA-256.
2. `document.xml`: every `w:p` text sequence, in document order
   (including table-cell paragraphs — index them globally).
3. Headings: order, styleId, text, position (81 H1 / 430 H2 example).
4. Tables: row count, cell count per row, vMerge/gridSpan, cell text
   sequence. (Zero structural diff + shading noise = "tables unchanged".)
5. Media parts: name/size/SHA-256 (13/13 identical ⇒ image conclusions
   from the old version still valid).
6. `document.xml.rels` and every `.rels`; relationship type counts.
7. `styles.xml`, `numbering.xml`, `settings.xml` — byte-identical is the
   strong result; document the differences when not.
8. `docProps/core.xml`, `app.xml`, `custom.xml` — tag-level diffs.
9. Security scan on BOTH versions: macros/OLE/ActiveX/comments/
   footnotes/endnotes/external rels/unknown parts.

Assertion gate: if the body-text diff is NOT exactly the one expected
change, or tables/media/relations/styles show unexpected change at the
semantic level, STOP and report `Unexpected Source Delta` — do not
update the baseline.

## Efficient large-XML differencing

Do NOT run `difflib.SequenceMatcher` over ~1.3M XML elements — it timed
out at 300 s in one real case. Instead:

- Compare paragraph/table **subtree canonical hashes** in document
  order (O(n)): serialize each subtree as tag|sorted-attrs|text, hash,
  zip-compare the two documents' block lists. This found exactly 12
  paragraph + 149 table blocks differing in seconds.
- For each differing block, tokenize on `<` and diff tokens (or diff
  `w:t` texts separately from property tokens) to classify property vs
  text changes.
- Beware a regex like `w:(rsid\w*)="..."` returning 0 hits: some
  producers write no rsid attributes at all — absence of rsids is not
  evidence of byte-identity.

## CRLF/LF false-mismatch trap

Reading a text file in binary mode and splitting on `\n` leaves `\r` on
every line; comparing that against regenerated content (or against a
text-mode read) reports hundreds/thousands of false mismatches. Always
normalize: read text files in text mode (universal newlines) or
`rstrip("\r")` every line before comparison. One real audit initially
reported 5,702 paragraph + 172 table "mismatches" that were 100% CRLF
artifacts; after normalization: 0.

## Concurrent-writer / parallel-session discipline

Multiple agent sessions can work the same work directory. Symptoms that
another instance wrote a file you thought you owned:

- File mtime is NEWER than your last write to it, or newer than your
  session's start while you did not write it.
- Content contains sections you never wrote (e.g. a §8 rebaseline
  record with locators you never computed), or your patch target string
  matches TWICE (duplicate section headers).

Rules that prevent damage:

1. Before patching any shared work file, re-read it and check mtime.
   If it changed since you wrote it, treat it as another instance's
   output: audit, then merge — never patch blind.
2. If `patch` reports 2+ matches for a supposedly unique anchor, STOP
   and inspect the file; a previous (parallel) writer may have appended
   the same section you are about to add.
3. When you do accidentally clobber (e.g. replaced §7 with your §8 and
   left a duplicate §8): restore the original text from your earlier
   read, keep ONE authoritative merged section, and preserve the
   parallel instance's original wording verbatim as an appendix —
   record the mistake in the report, do not hide it.
4. Two instances reaching the same conclusion independently is
   corroboration; record both provenance trails (script mtimes, report
   timestamps) rather than deleting the other's artifacts.
5. Lock-file gate: before rebaselining a file that may be open in an
   editor, check for `~$*` owner files next to it. Present ⇒ the
   document may still be open ⇒ pause (`Source Still Open`), do not
   modify. Also do the stability double-check: hash, do a full
   structural read, hash again; both must equal the expected anchor.

## Pitfalls

- **Never write a plausible-looking hash into a report/inventory** —
  placeholders get caught by the next audit (one real case: 13 image
  SHA-256 cells, 6 of them not even 64 hex chars, all wrong). Compute,
  copy verbatim from live output, and verify against a second source.
- **"已登记" ≠ "已提取" ≠ "已核验"**: when covering a large document,
  keep per-item states explicit (Registered / Extracted / Visually
  Checked / Structure Preserved / Unreadable / Pending / Excluded) and
  report each count separately.
- A `documentProtection` element with `w:enforcement="0"` is an inert
  placeholder (WPS writes it routinely) — not actual protection.
- `custom.xml` (KSOProductBuildVer/ICV/KSOTemplateDoc) is WPS
  metadata-only; register it, do not treat as content.
