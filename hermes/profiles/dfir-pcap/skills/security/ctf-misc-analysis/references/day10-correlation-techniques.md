# Day 10 — Multi-source event correlation (comprehensive capstone)

Methodology for a multi-artifact case where one main case_id is spread across several
independent sources (access log, PCAP, browser history, registry hive, disguised file)
plus a decoy case. Validated 2026-08-28 (SecurityLab bootcamp Day 10; teacher first
review 90/100 — one structured-field transcription error, corrected; final re-verification
pending at the time of writing).

## Top-level flow

Preserve → Triage (per source: what it CAN and CANNOT prove; main vs decoy candidates)
→ Hypothesis → Collect (structured fields only, no flag-regex across files)
→ Correlate (cross-source IDs/hashes/URIs/sequences) → Validate (byte-level, ≥2 sources)
→ Timeline (each field's own epoch) → Conclusion → Report.

## Hard rules that came out of this case

- **sequence ≠ time.** A `sequence`/`seq` field orders structured fragments (1..5) for
  assembly; it NEVER orders events in the timeline. Build the timeline exclusively from
  each source's own timestamp fields.
- **Three-source object-hash verification.** One object's SHA-256 must agree byte-for-byte
  across: (1) protocol header declared value (e.g. `X-Artifact-SHA256`), (2) application
  record (e.g. Chromium `downloads.hash` BLOB — raw 32 bytes, hex it), (3) the file on
  disk (recomputed). Also compare the PCAP-reassembled response body vs the file bytes.
- **Content-Type is a claim, not evidence.** A response declared `image/jpeg` with
  `Content-Length` matching the .jpg on disk is still a ZIP if the bytes say `50 4B 03 04`.
  Verify magic + ZIP local header/central directory/CRC (`zipfile.testzip()`) before
  trusting any extension or MIME label.
- **Decoy exclusion needs ≥2 independent reasons.** A decoy case was excluded because:
  case_id differs, its sequences were discontinuous (1,3,5 — gaps), its object never
  downloaded (HTTP 404, no body), and its fragments were meaningless when joined.
- **Internal timestamps are not transferable.** A ZIP manifest `created_at` (inside the
  container) ≠ download time (PCAP frame/header timestamp, browser download start/end)
  ≠ Registry LastWrite. Record all three and state explicitly they are not interchangeable.
- **Fragment assembly is literal.** Join fragments in sequence order without "fixing"
  the text (a fragment without a trailing underscore joins directly onto the next one;
  the result may read oddly — that is the design, not a decode error). Decode each
  fragment_b64 independently first, then join.

## Structured-field transcription discipline (teacher correction, 90/100)

A hand-transcribed Base64 fragment was corrupted between tool output and the report
(`YmVhdHNf`=beats_ recorded as `YmVhcnNlZA==`=bearsed), which then polluted the assembled
flag, summary, conclusions and self-score. Lessons:

- **Capture every structured field twice, from independent implementations, and require
  byte-identical results.** For PCAP: Implementation A = TShark field extraction
  (`-Y "frame.number==N" -T fields -e http.response.line` — note `http.header` is NOT a
  valid field in TShark 4.2.0; `http.response.line` carries the whole header block with
  embedded `\r\n`); Implementation B = raw byte reassembly (parse pcap records, rebuild
  the server→client stream BY TCP sequence numbers — not display order, and never mix
  two TCP streams' seq spaces; split the header block on `\r\n\r\n`; print each header
  line as hex + ASCII). The tool's own earlier output can prove the corruption was in
  transcription: the original follow-stream hex already contained the correct value.
- **Keep the audit chain** raw-field (hex+ASCII) → decoded bytes → UTF-8 text → assembled
  result, all saved to the remediation workdir.
- **Base64: two decoders + re-encode check.** stdlib `b64decode(validate=True)` AND an
  independent manual decoder must agree on bytes; re-encoding must reproduce the input;
  check charset/length-mod-4/padding. Never accept a decode just because the text
  "looks natural".
- **Assert before assembling:** same case_id across all fragments, sequence exactly
  1..N continuous, no duplicates, no gaps; decoy fragments excluded.
- **Semantic unnaturalness is a review trigger, not evidence.** A decoded fragment that
  reads oddly (`bearsed`) was the artifact of the transcription error — but semantics
  can only flag a suspicion; the byte evidence decides.
- **Root-cause discipline:** distinguish Observation (what the bytes actually say, both
  impls identical) / Error Propagation / Root Cause / Prevention / Evidence Boundary.
  When the original tool output was already correct, the corruption is between "raw
  field read and report record" (transcription/copy) — do not blame the tool or the
  decoder, and do not over-specify the exact keystroke.
- Teacher-provided values are acceptance anchors only — reproduce them from local
  evidence independently; if local evidence disagrees, STOP and report the conflict.

## Per-source recipes

### Access log (W3C extended format)
Parse by the `#Fields:` header line, never by column position. Fields seen:
`date time c-ip cs-method cs-uri-stem sc-status request_id case_id sequence fragment_b64 artifact_id object_sha256`.
Note: the log may cover requests outside the PCAP capture window — that is a coverage
difference, not a contradiction; say so.

### PCAP → HTTP response body
Two reliable paths:
- `tshark -r x.pcap -Y "http.response" -T fields -e frame.number -e http.content_length -e http.file_data`
  → `http.file_data` gives the response body as hex directly (cleanest).
- `tshark -r x.pcap -q -z follow,tcp,raw,<stream>` → the hex line comes AFTER the
  `Node 0/Node 1:` lines, not on line 2 (`sed -n '/^Node 1:/,/^$/p'` then strip); a naive
  `sed -n '2p'` grabs the `Filter:` line and yields an empty body.
Read custom headers (case/sequence/fragment_b64/artifact_id/object_sha256) from the raw
HTTP header block between `\r\n\r\n` splits.

### Browser history (Chromium-style SQLite)
`PRAGMA table_info` / `sqlite_master` first. Standard tables: urls, visits, downloads,
downloads_url_chains. Joins: `visits.url -> urls.id`, `downloads.id -> downloads_url_chains.id`.
- WebKit timestamps = **microseconds since 1601-01-01 UTC** → ISO 8601 UTC via
  `datetime(1601,1,1,tzinfo=utc) + timedelta(microseconds=t)`.
- `downloads.hash` BLOB is the raw 32-byte SHA-256 of the downloaded file.
- Distinguish `tab_url` (the page that initiated the download) from
  `downloads_url_chains.url` (the actual download chain URL) — they can differ by host.
- `received_bytes/total_bytes = 0` with `state=1` is possible in training fixtures;
  record it as-is, flag it, do not "repair" it.

### Registry hive
Reuse the Day 9 reference (regf XOR checksum over 0x000–0x1FB vs stored @0x1FC;
NK name_len@0x48/name@0x4C single-byte; VK sig/name_len@2/len@4 (`0x80000000` inline
flag)/data_off@8/type@0xC/name@0x14; offsets +0x1000 relative to first HBIN).
MRUList gives access ORDER (e.g. "abc"), which is not the fragment sequence order.
Registry presence of a case_id/fragment is static evidence — never claim execution.

### Disguised file (ZIP named .jpg)
- Magic `50 4B 03 04` + `file` verdict + `testzip()` CRC all-pass = ZIP, regardless of
  extension/Content-Type.
- The inner manifest (JSON) can itself carry `actual_container`, `artifact_id`,
  `case_id`, `content_type_claim`, `fragment_b64`, `sequence`, `created_at` — treat
  `content_type_claim` and `created_at` as claims, cross-check against bytes and
  download/registry timestamps.
- A second manifest inside the same container may belong to the DECOY case — separate
  by case_id before assembling.

## Cross-source correlation matrix (do all of these)

1. artifact_id consistent across sources (log / PCAP header / manifest).
2. object SHA-256: header-declared ⇄ downloads.hash BLOB ⇄ file bytes ⇄ response body.
3. PCAP request URI == browser download-chain URL (same object).
4. main-case sequence 1..N continuous, no duplicates/gaps.
5. decoy case: why it cannot join the main timeline (≥2 reasons).

## Timeline construction

One row per event: `Timestamp(UTC) | Source | Event | Evidence(raw field value) | Confidence`.
Convert each field with its OWN epoch/unit (log seconds UTC; WebKit µs-1601; FILETIME
100 ns-1601; HTTP header ISO strings). Merge rows for the same event across sources but
keep each source's raw evidence. Confidence: High for byte-level proof; High(static) for
timestamps that are embedded metadata (manifest created_at, registry LastWrite).

## Report skeleton (13 sections)

Executive Summary · Scope · Evidence Inventory · Tool Health · Per-Source Findings ·
Correlation Matrix · Incident Timeline · Validated Conclusions · Confidence Assessment ·
Alternative Explanations · Unresolved Questions · Evidence Integrity · Project Memory Update.
Each conclusion: Observation / Inference / Alternatives / Conclusion / Next Validation
with real commands + real output + extracted-artifact path/size/full SHA-256.
