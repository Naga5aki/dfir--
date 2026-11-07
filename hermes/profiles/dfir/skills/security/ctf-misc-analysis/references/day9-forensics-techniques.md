# Day 9 lightweight forensics (SQLite WAL / Git bundle / registry hive / Chromium)

Recipes from the SecurityLab bootcamp Day 9. Core mantra of the class: **current state ≠ historical state** (WAL frames, Git blobs, deleted/overwritten records) and **timestamp fields: confirm epoch/unit/timezone before converting**.

## Timestamp epochs cheat-sheet
- Unix: seconds since 1970-01-01.
- SQLite app columns: read column-name semantics (e.g. `*_us` = Unix microseconds).
- **FILETIME**: 100 ns since 1601-01-01 UTC (registry NK LastWrite, NTFS).
- **WebKit** (Chromium History): **microseconds** since 1601-01-01 UTC — NOT Unix seconds/millis.
- Report raw integer + epoch/unit/timezone interpretation + ISO 8601 UTC together.

## SQLite WAL + deleted/overwritten rows
- Copy main db + `-wal` + `-shm` as a GROUP to work; hash all three. Open read-only (`file:xxx?mode=ro`) so no checkpoint / no write.
- WAL header (32 B): magic field read BIG-endian = `0x377f0682` (that value denotes little-endian frame checksums; `0x377f0683` = BE) — LE read of the bytes gives `0x82067F37`, so read BE for the value. version @4, page_size @8, ckpt_seq @12, salt1 @16, salt2 @20, cksum1/2 @24/28.
- Frame indices are ZERO-BASED: "frame index 0" = first frame in the WAL (NOT the header), frame index 1 = next. Say "frame index N" explicitly to avoid the header ambiguity.
- Frame i: 24-B frame header (page_no, commit_dbsize, salt1, salt2, cksum1, cksum2) at `32 + i*(24+page_size)`; the page image starts at `+24` (off-by-24 is the classic bug). commit_dbsize > 0 marks a commit frame.
- Historical frame = older version of a page; the newest frame for that page = current logical state. Parse the b-tree page:
  - page header (8 B): type@0 (5=interior, 13=leaf), first_free@1, n_cell@3, cell_content@5, fragmented@9; cell-pointer array at offset **8**, 2 B each.
  - leaf cell: payload_len varint, rowid varint, then record.
  - record: header-size varint, then serial-type varints until `off+hdr`, then values. Serial types: 0=null, 1=1B, 2=2B, 3=3B, 4=4B, 6=8B int, 7=8B float, odd ≥13 = text `(t-13)/2` B, even ≥12 = blob `(t-12)/2` B.
- Prove a recovered row is NOT in the current logical state via the read-only SELECT; raw bytes in a historical frame ≠ "recovered record".
- **Evidence boundary (teacher-corrected): page versions cannot determine the SQL verb.** Two page versions only prove "the content stored for that ROWID differed". Whether the middle operation was UPDATE vs DELETE-then-INSERT is NOT uniquely determinable: without AUTOINCREMENT, SQLite allocates ROWID from the current max still present, so DELETE(max)+INSERT reuses the same ROWID and the latest state still shows that id. "The id still exists" does NOT prove UPDATE; "row count unchanged" does NOT disprove DELETE. Only SQL logs or generator facts settle it — label the action sequence as "generator fact" when only the generator knows.
- Cross-check: independent parse of the newest frame must equal the sqlite3 SELECT output.

## Git bundle history
- `git bundle verify` needs a repo context: `mkdir v && git init -q v && git bundle verify <bundle>` (or just clone — clone validates).
- `git clone bundle repo` → `git log --all --full-history --name-status --format="COMMIT %H%nPARENT %P%nAUTHOR %ai%nSUBJ %s"`.
- Deleted files: `git show <commit>:<path>` reads the historical blob; blob SHA via `git rev-parse <commit>:<path>`. Current worktree absence proves nothing. Don't rely on reflog (bundles don't carry it). Never execute hooks/scripts/binaries from history.

## Registry hive (offline, no reg load)
- regf header: magic `regf` @0, seq1/seq2 @4, root cell offset @36 **relative to the first HBIN data area → add 0x1000 for file offset**, hive-bins data size @40, header checksum @508.
- **Header checksum — STANDARD algorithm (teacher-corrected; a false "generator variant" conclusion was reached by summing instead of XORing)**: XOR the 127 little-endian DWORDs covering offsets 0x000–0x1FB (0x1FC bytes; do NOT include the stored field) and compare with the LE DWORD at 0x1FC. Two independent impls that agreed: byte-loop `struct.unpack_from("<I", h, off)` accumulated with `^=`, and `functools.reduce(operator.xor, struct.unpack("<127I", header[:0x1FC]), 0)`. Both matched stored on a real hive. **If computed ≠ stored, debug offset / endianness / loop end / accidentally including the stored field / truncation / corruption / parser first — never default to "generator variant".**
- Cell: 4-B signed size (negative = allocated), data follows at +4.
- **NK** (key): sig(2) flags(2) LastWrite(FILETIME)@4 subkey_count@0x14 subkey_list@0x1C volatile_list@0x20 value_count@0x24 value_list@0x28 security@0x2C class@0x30 max_subkey@0x34 max_class@0x38 max_value@0x3C workvar@0x40 name_len@0x48 class_len@0x4A **name@0x4C**. Key names were single-byte ASCII in the training sample (decode latin1; beware UTF-16 on Unicode hives).
- Subkey lists: `lf`/`lh` = 8-B entries (offset+hash), `li` = 4-B offsets. Value list: cell at value_list offset, offset array inside cell data (+4).
- **VK** (value): sig(2) name_len@2 len@4 (high bit `0x80000000` = inline data) data_off@8 type@0xC flags@0x10 spare@0x12 name@0x14. Types: REG_SZ=1, REG_DWORD=4. Names single-byte ASCII in sample; REG_SZ data was UTF-16. len ≤ 4 → inline after name; else data at `data_off` cell.
- MRU keys: `MRUList` value gives the order string (e.g. "cba") — concatenate values `a<ch>` in that exact order (alphabetical order is a trap).
- NK LastWrite is the key's last-write time only — cannot attribute to a specific value. **Identical FILETIME values across keys prove only that those NKs store the same LastWrite value — NOT write count, NOT the writing tool, NOT the per-value modification time.**
- Value names single-byte ASCII in the training sample (decode latin1; beware UTF-16 on real hives); REG_SZ data was UTF-16.

## Chromium History
- Tables: urls(id,url,title,last_visit_time), visits(id,url,visit_time,from_visit,transition,visit_duration), downloads(...start_time,end_time,tab_url), downloads_url_chains(id,chain_index,url).
- Timeline: `visits.url → urls.id` JOIN ordered by `visit_time` (WebKit µs). Titles/URLs in visit order often reassemble the payload.
- downloads: `tab_url` = originating page URL; `downloads_url_chains.url` = actual download-chain URL (different things). start/end = WebKit µs.
- `urls.last_visit_time` is NOT a substitute for per-visit times (only the last visit).

## Deliverable discipline (teacher-verified)
- Full 64-char lowercase SHA-256 everywhere (8-char prefixes were penalized).
- **Second correction (91/100): hashes must be verbatim, never padded.** The "complete" 64-char SHA-256s in the report were wrong: only the first 8 chars were real (from the SHA256SUMS manifest); the trailing 56 chars had been written from memory/invention ("前 8 位真实，后续字符并非现场 Get-FileHash 结果"). A hash whose tail you did not observe is **fabricated evidence**. Copy only from live command output — `sha256sum` / PowerShell `Get-FileHash -Algorithm SHA256`; never extend a prefix, never "fix" a file to match a wrong hash.
- **Triple-source verification** for sample hashes: (a) `Get-FileHash` on the work copy, (b) `SHA256SUMS.txt` in the package, (c) an INDEPENDENT recompute of each member read straight out of the outer archive (`zipfile`/`unzip -p`). All three must agree; sizes checked with `Get-Item`/`wc -c` in the same pass (sample01 was 1,020B, not the 4,215B assumed from archive size; scripts were 1,591/3,510/2,012B, not the guessed 1,169/2,943/2,111B).
- **Residue scan after replacement**: grep both reports for unique fragments of each WRONG value (chars 9–16 — position 1–8 are shared with the correct hash) and require 0 hits; wrong sizes may survive only inside text explicitly labeled "historical error / 误记". Don't write the wrong full hash into the correction section itself.
- **Label hash algorithms distinctly**: Git commit/blob object ids are **SHA-1**; file hashes are **SHA-256**. Never blur them under one "SHA".
- **Re-verify file sizes on disk** (`wc -c`) when reporting — an earlier note said 32B but the file was actually 33B (content and hash unchanged; the record was wrong, not the file). Don't "fix" the file to match the old note.
- Tool versions: read **PE VersionInfo read-only** via PowerShell `Get-Item <exe> | Select-Object -ExpandProperty VersionInfo` (FileVersion/ProductVersion) — no GUI launch needed. If the GUI can't run in the environment, record that honestly; never claim GUI validation passed.
- Reports need the actual commands + their real output, per question ("Command / Relevant Output"), including the failing-before/fixed-after pair where applicable.
- Playbook numbering must be globally unique across the whole project memory (a renumbering audit happened on Day 7/8).
- State machine: initial status → Remediation Required (teacher first check) → Remediation Completed → teacher final re-verification (text-only status sync afterwards).
