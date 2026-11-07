# Day 5 teacher corrections (SecurityLab, 2026-08-26)

Teacher's directed text corrections that SUPERSEDE the first-round notes in
`day5-archive-techniques.md` (97/100 first pass; these three fixes complete
the round). Reuse the STRUCTURE, not the values.

## 1. ZIP Extra Field is FIXED TLV — no "1/2-byte size" ambiguity
- The generic ZIP Extra Field structure is fixed: Header ID (2 bytes, LE) +
  Data Size (2 bytes, LE) + Data (of Data Size length). Do NOT report a
  "1-byte size variant" of 0x5455; there is none. The 2-byte Data Size
  structure is not negotiable.
- Example (9-byte field `55 54 05 00 01 80 2c 8e 6a`): Header ID = 0x5455,
  Data Size = 5, Data = flags byte 0x01 (mtime only) + mtime `80 2c 8e 6a`
  LE = 1787702400 = 2026-08-26 00:00:00 UTC. 4-byte header + 5-byte data =
  9 bytes exactly, no stray bytes.
- 0x5455 payload: first byte = flags; timestamps follow per flags bits
  (mtime bit0 / atime bit2 / ctime bit3), each 4-byte LE unix time in UTC.
- DOS vs Extended-Timestamp conflict still proves ONLY metadata
  inconsistency — never a tamperer, tool, or real event time by itself.

## 2. Pseudo-encryption — bounded conclusions only
- Clear bit 0 in BOTH Local Header and Central Directory on a work copy.
- Extraction OK + usize correct + CRC match ⇒ pseudo-encryption SUPPORTED.
- Extraction failure OR CRC mismatch ⇒ only "pseudo-encryption NOT
  confirmed". Continue to distinguish: real ZipCrypto, AES, data corruption,
  wrong compressed-data cut, structural anomaly. Never jump to "real
  encryption" from a single failed check.

## 3. raw DEFLATE verification — valid independent check
- `python -m zlib` is NOT a valid command (no executable module entry) —
  never list it as a verification method.
- Prescribed independent verification: read-only script with
  `zlib.decompressobj(wbits=-15)`; assert `eof is True`, `unused_data`
  empty, `unconsumed_tail` empty, and output size + SHA-256 match the first
  extraction. `file(1)` type identification is only auxiliary evidence.

## 4. Reporting discipline (applies to every round)
- Keep an explicit "teacher correction record" in the original report — never
  pretend the first round was fully correct; record before/after for each
  corrected item in a separate remediation report.
