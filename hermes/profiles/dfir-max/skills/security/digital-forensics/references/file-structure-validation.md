# File-structure validation and anomaly reasoning

Use this reference after basic unknown-file triage when the task requires format completeness, ordering, offsets, checksums, or object relationships—not merely a type label.

## Core sequence

1. Preserve scope and hash every original before reading deeply.
2. Run independent basic classifiers and inspect the header/trailer with hex tools.
3. **Manually map structure before using a specialist validator or decoder.** A parser opening the file is corroboration, not proof that ordering, checksums, or terminal structures are valid.
4. Save raw outputs outside evidence. Put helper scripts and generated JSON in a work area.
5. Resolve every warning or disagreement at the raw field offset and width.
6. Re-hash originals and mechanically compare manifests.

For each anomaly report exactly:

- **Observation:** directly observed bytes, offsets, declared lengths, references, or checksum comparison.
- **Inference:** the narrow explanation supported by those facts.
- **Alternative Explanations:** at least one other cause still compatible with the evidence.
- **Conclusion:** the narrowest defensible status; preserve uncertainty.
- **Next Validation:** the evidence needed to distinguish the alternatives.

## PNG: chunk walk and CRC discipline

After the 8-byte signature, each chunk is:

```text
chunk_start +0   4-byte big-endian Data Length
            +4   4-byte Chunk Type
            +8   Data (Length bytes)
            ...  4-byte big-endian stored CRC
```

For each chunk record:

- chunk start;
- Data Length;
- Type;
- inclusive Data range (or empty);
- CRC offset;
- stored CRC;
- independently computed CRC;
- complete/incomplete boundary status.

CRC is computed over **Type + Data only**, never the Length field. Use at least one standard implementation and, when the checksum is disputed, a second independent implementation (for example a pure bitwise CRC-32 routine) before reporting a mismatch.

Validate separately:

- signature;
- IHDR is first, appears once, and has expected length/fields;
- one or more IDAT chunks exist and multiple IDAT chunks are consecutive;
- IEND exists once, has zero Data Length, is last, and ends at the file boundary;
- no bytes follow IEND;
- the file ends on a complete chunk boundary;
- concatenated IDAT data decompresses and has the expected scanline length when the IHDR parameters make that calculation possible.

### PNG reasoning boundaries

- A CRC mismatch proves only that the stored CRC differs from the CRC of the **current** Type+Data. It does not identify which field changed, the cause, or a correct repair value.
- A missing IEND proves that the PNG datastream lacks its required terminal chunk. If the file ends exactly after another complete chunk, report that fact too. Do not attribute the absence to truncation, transmission loss, or deliberate deletion without provenance evidence.
- Decoder success does not erase a CRC/order/IEND defect. Decoder failure does not identify its cause.

## JPEG: marker-aware parsing

Do not stop at `FF D8`. Walk markers in order and record each offset and declared length:

- SOI;
- APP/JFIF/Exif as present;
- DQT;
- SOF (capture precision, dimensions, and component count);
- DHT or other coding tables;
- SOS;
- entropy-coded scan data;
- EOI.

JPEG segment lengths include the two-byte length field but not the marker bytes. Verify every segment end is within the file.

Inside entropy-coded data:

- `FF 00` is a stuffed data byte, not a marker;
- `FFD0`–`FFD7` are restart markers;
- an unstuffed non-restart marker ends the current scan.

Confirm EOI exists, count it, record its offset, and distinguish exact EOF from trailing bytes.

## ZIP: two header views plus EOCD

Locate Local File Headers, Central Directory entries, and EOCD. For every member compare Local versus Central values:

- filename;
- flags;
- compression method;
- CRC-32;
- compressed size;
- uncompressed size;
- Local Header offset.

Verify:

- EOCD entry counts;
- Central Directory offset and size;
- `central_offset + central_size == EOCD offset` for a simple single-part archive;
- EOCD/comment length reaches the actual file boundary;
- each Central Directory Local Header offset points to `PK 03 04`;
- in-memory decompression length and CRC when policy permits read-only validation.

Do not extract members into evidence or execute them.

A keep-going classifier (for example `file -k`) may emit secondary magic matches that conflict with exact offsets. Do not vote between strings. Re-run the plain classifier, inspect offset 0, and compare with `zipinfo`/EOCD arithmetic before claiming prepended data.

## PDF: object and reference graph

For classic-XRef PDFs record:

- `%PDF-x.y` header;
- every indirect object number/generation and byte offset;
- `endobj` presence;
- stream `/Length`, data start, and whether the declared length lands at `endstream`;
- XRef offset and entries;
- Trailer `/Size`, `/Root`, and `/Info` as present;
- `startxref` keyword, numeric value, and actual target;
- `%%EOF` offset and whether only permitted whitespace follows.

Cross-check every in-use XRef offset against the corresponding object. Resolve Root to a Catalog, Catalog to Pages, Pages to Kids, and each Page back to its Parent. Compare `/Count` with the resolved page kids at the granularity the file supports.

When a dedicated validator is unavailable, raw object/XRef validation plus independent `file`/ExifTool results may support a structural conclusion, but report the missing validator as a coverage limitation—not as a permanent tool incapability.

## Optional validator failures

If an optional decoder/import fails because of the current environment:

1. retain the exact failure and exit status;
2. do not claim the validator ran successfully;
3. continue with already validated raw-structure methods when sufficient;
4. state what an operational validator would add;
5. avoid persisting the transient failure as a durable claim about the tool.

## Reporting tables

For PNG, use one row per chunk with offsets, length, type, Data range, CRC offset, stored/computed CRC, result, and structural note.

For JPEG, ZIP, and PDF, use ordered structure tables or compact offset diagrams. Preserve full raw outputs separately; the report should explain evidence rather than paste it.
