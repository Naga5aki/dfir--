# Day 8: Document & Text Steganography Recipes (PDF / OOXML / SNOW / Zero-Width / NTFS ADS)

SecurityLab bootcamp Day 8 — verified on benign offline samples. Structure-first discipline applies: locate via format structure (objects, parts, relationships, streams, line endings), never regex-scan for the flag. **Static presence ≠ execution**: PDF JavaScript actions, Office macros, and extracted files are evidence of existence only; say so explicitly in conclusions.

## Tool baseline (all CLI, read-only)

- qpdf (Windows): `--qdf --object-streams=disable --decode-level=all` expands object streams and decompresses streams into a readable QDF. `--check` first for syntax/stream errors. Attachments: `--list-attachments` → `evidence.txt -> 6,0` (key = name, target = obj,gen), `--show-attachment=<key>` writes the bytes to stdout (qpdf 12.x has NO `--save-attachment`/`--extract-attachment`; redirect stdout). `--json` gives attachments/filespec/streams structure.
- 7-Zip: `l -slt -sns` lists alternate streams inside containers (WIM preserves ADS; `.7z` replying "not implemented" is a container/implementation boundary, NOT proof the sample has no ADS). `x` from WIM preserves ADS on NTFS.
- PowerShell: `Get-Item <file> -Stream *` lists `:$DATA` + named streams with lengths; `Get-Content -Path <file> -Stream <name>` reads a named stream.
- ExifTool 13.59: metadata (not page text) on PDFs.

## PDF: object streams & invisible text

1. `qpdf --check` (PDF version, encryption, syntax). Then establish the object/cross-reference structure BEFORE expanding: `qpdf --show-xref` (per object: `uncompressed; offset = N` vs `compressed; stream = S, index = I`) and `qpdf --show-pages` (page object → its `/Contents` target object).
2. **`/ObjStm` members vs page content stream are two separate facts.** A stream object cannot be a regular member of `/ObjStm`. A file may compress objects 2/0-5/0 into an ObjStm while the content stream is a standalone **uncompressed** xref object (e.g. `6/0: uncompressed; offset = 292`). Never claim "the content stream came out of the ObjStm" just because the PDF contains one — verify membership per object (show-xref: compressed = ObjStm member; uncompressed = standalone stream object). `qpdf --qdf --object-streams=disable --decode-level=all` expands ObjStm members and may renumber them; QDF comments `%% Original object ID: N M` map QDF numbers back to the originals.
3. In the content stream (BT/ET blocks), inspect the color operators per text block: `0 0 0 rg` = black (visible), `1 1 1 rg` = white fill — on a white page that text is **invisible**. `rg` sets non-stroking fill color; no `Tr` (rendering mode) operators needed for this trick. Report the operator-level difference between visible and invisible content.

## PDF: attachments & actions

Object chain: Catalog `/Names /EmbeddedFiles /Names [(name) <filespec-ref>]` → Filespec (`/F /UF /EF`) → `/EF /F <embeddedfile-ref>` → EmbeddedFile (`/Type /EmbeddedFile`, `/Subtype /text#2fplain` → MIME) → stream (the bytes). Cross-check with `qpdf --list-attachments` + `--show-attachment`.
Actions: Catalog `/OpenAction <obj> R` = `/S /JavaScript /Type /Action` with `/JS` text. If the JS is a comment-only string ("no calls, no side effects"), it is **inert/lazy code** — record "static action exists, execution NOT proven". Never open the PDF in a script-capable reader.

## OOXML (DOCX/DOCM as ZIP)

1. Enumerate parts: `[Content_Types].xml` (Default/Override ContentTypes — main doc part, comments, media extensions), `_rels/.rels` (officeDocument relationship), part-level rels (`word/_rels/document.xml.rels`: comments, image, vbaProject relationships with their Ids), `word/comments.xml`, `word/media/*`.
2. **Relationship Target normalization**: Targets in a part's rels are relative to that part — resolve `comments.xml` from `word/_rels/document.xml.rels` → `word/comments.xml`; never guess paths.
3. Split flag pieces carry explicit labels (e.g. `part-a:` in comments.xml, `part-b:` in a PNG tEXt Comment chunk) — combine by the labels.

## Macro-enabled OOXML (static evidence only)

Confirm: extension `.docm`; main-doc ContentType `application/vnd.ms-word.document.macroEnabled.main+xml`; relationship Type `.../vbaProject` → Target `vbaProject.bin`; the bin's magic `d0 cf 11 e0 a1 b1 1a e1` (CFB compound file).

Minimal CFB directory walk (MS-CFB header offsets, 512-byte sectors):
- sector_shift @30 (usually 9 → 512B), n_FAT @44, first_directory_sector @48, mini_stream_cutoff @56 (default 4096 — **NOT the FAT count**), DIFAT[0] @76 (first FAT sector).
- FAT sector at `512 + difat0*512`; walk directory chain via FAT; each 128-byte dir entry: name_len @64 (UTF-16LE, name_len-2 bytes), type @66 (5=root, 2=stream, 1=storage), start_sector @116, size @120 (8B).
- **Real VBA project module parsing** (teacher-corrected: do NOT judge compression by the stream's first byte): parse the project's `dir` stream MODULE records to get module stream names + MODULEOFFSET/TextOffset; the module stream's head is an implementation/version-dependent **PerformanceCache** (length = MODULEOFFSET, skip it); only the **CompressedSourceCode starting at TextOffset** is an MS-OVBA compressed container (3-byte header + 2-byte chunk headers, 0x0FFF = raw chunk, tokens 0x00/0x01-0x0FFF = literals, 0x2000-0x2FFF = back-copy).
- A minimal training CFB (directory holds only Root Entry + one module stream, no `dir`/PROJECT/PROJECTwm metadata) may carry VBA-shaped plaintext — label it honestly as "non-standard/minimal training CFB with VBA-shaped text", NOT a complete standard VBA project, and do not elevate the sample's plaintext into a general parsing rule.
- Macro parts existing ≠ macro ran; a "never executed" comment is itself static evidence.

## SNOW (line-ending whitespace)

Preserve original bytes (no editor that strips trailing whitespace). Read binary, split on CRLF; per logical line collect FOUR statistics: (a) full trailing-whitespace length, (b) spaces total inside the trailing region, (c) tabs total inside it, (d) terminating spaces after the LAST tab. **The four are different numbers and only (d) is "spaces after last tab"** — never write "the line ends in N spaces" from (d) alone; the SNOW payload is composed of MULTIPLE tab/space groups per line. Verify: CRLF count, fragment count (last fragment empty after split), the four-way table. Extract with `SNOW.EXE -C <file>` (-C = compressed mode; the output also passes through a compression layer); without -C you may get raw bits + "residual of N bits not output".

**Extraction mechanics (verified round-trip):**
- **Mode must match the payload — wrong mode fails silently.** Compressed payload decoded without -C → hex garbage + `residual of N bits` warning; raw payload decoded with -C → plain garbage string, no error. Mode unknown ⇒ try both and validate the output; "it ran" proves nothing.
- **Decode success ≠ correct message.** One flipped whitespace char (space↔tab) still exits 0, no warning, message silently corrupted. Validate every extraction: expected prefix (`xorkey:` / `key:` / `stream=...`), printability, downstream recompute (XOR/CRC/format). A `xorkey:<key>` body marks the companion hex/base64 ciphertext as repeating-key XOR; a wrong near-key corrupts ONLY the key-cycle positions (near-miss signal, not a second answer).
- Line endings: CRLF→LF conversion doesn't change the extracted bits (whitespace sequences only; `\r` ignored) — both tools decode either way — but preserve original bytes as discipline.
- Capacity = total trailing whitespace chars (spaces+tabs). **Encode: `SNOW.EXE -C -m "<msg>" <carrier> > <out>` — encode reads the carrier and writes the encoded text to stdout; it does NOT modify the carrier in place** (no redirect ⇒ nothing happened; the untouched carrier decodes to nothing). Payload overflowing: stderr `Message exceeded available space ... An extra N lines were added.` — read stderr for capacity notes.
- Arsenal MCP `snow` tool ≡ classic SNOW.EXE (correct decode / empty payload / both mode-mismatch paths byte-identical) — use as the two independent implementations for cross-validation.
- **Work order (Transfer-Validated: original + 3 transfer variants + boundary LF case + 3 negative controls):** classify the carrier → run BOTH modes with the canonical tool first (~30 s) → shape-check the message (prefix / printability / downstream recompute) → only then hand-read bits at all (structural profiling, ≤1 round). Two rounds without a clean hit ⇒ switch to the tool — near-text noise from hand-reading is the switch signal.

## Zero-width characters

From the ordinary data stream, walk Unicode code points: ZWSP U+200B, ZWNJ U+200C, ZWJ U+200D, WJ U+2060 (also BOM/ZWNBSP, LRM/RLM). Map (e.g. ZWSP=0, ZWNJ=1), pack MSB-first per byte; try the inverted mapping as a control (should be garbage). The decoded bit stream is often an **instruction** ("stream=<name>;encoding=base64") pointing to where the real payload lives — follow it.

## NTFS Alternate Data Streams

1. Audit the container with `7z l -slt -sns` (name it: `carrier.txt:evidence`).
2. Extract to a **real NTFS** work directory, then confirm the stream truly exists: PowerShell `Get-Item -Stream *` shows `:$DATA` + named streams with lengths.
3. Read it with `Get-Content -Stream <name>`; base64-decode if instructed.
4. On non-NTFS filesystems ADS may not survive — report honestly and give the next validation step; never pass off a colon-named file as an ADS.

## Deliverable hygiene (carries over from Day 7 teacher feedback)

- Full 64-char lowercase SHA-256 everywhere (evidences, derivatives, scripts, tools), never 8-char prefixes.
- Real commands + key outputs per question (capinfos/qpdf/7z/PowerShell/scripts with exit codes), not "ran it".
- Playbook/note numbering must stay globally unique when appending (Day 7 once reused Day 6's P29-P31 — audit before assigning).
