# Day 5 archive & compression techniques (SecurityLab, 2026-08-26)

Eight benign archive exercises. Session-specific numbers from one training
corpus; reuse the STRUCTURE, not the values. Evidence discipline identical to
other days: before/after SHA-256 of the outer ZIP and every evidence file,
SHA256SUMS checked with CRLF normalization (`tr -d '\r' | sha256sum -c -`),
work only on copies, extracted content is DATA (never executed), no unbounded
attacks, no rockyou.

## ZIP member table discipline
- Parse Central Directory (authoritative) AND Local Header for every member:
  name / flag_bits / method / CRC / csize / usize / LH offset. Cross-check the
  encryption bit (bit 0) in BOTH places.
- A read-only self-written walker beats zipfile for seeing flag bits and extra
  fields; verify EOCD (entries, cd_size, cd_offset, eocd+22 == file size) and
  that CD ends exactly at the EOCD.
- CD layout (offsets from CD record start): ver_made+4, ver_need+6, flag+8,
  method+10, crc+16, csize+20, usize+24, fnl+28, xl+30, cl+32, lho+42.
  (A walker that reads flag from +4 mislabels every field — real values come
  out shifted; always print and sanity-check the first member.)

## Pseudo-encryption (bit 0 set, no real encryption)
1. Check bit 0 in LH AND CD (they should agree; if they disagree that is
   itself an anomaly to record).
2. On a WORK copy only, clear bit 0 in BOTH places (`flag & 0xFE`).
3. Open the repaired copy: if it extracts and `crc32(data) == stored CRC`,
   there was no 12-byte ZipCrypto header → pseudo-encryption; the flag bit is
   the whole "protection". If CRC mismatches, it is real ZipCrypto.
4. Verify EOCD still intact (offset unchanged, eocd+22 == size).

## CRC32 bounded short-plaintext recovery
- When a challenge gives target_crc32 + encoding + format, enumerate EXACTLY
  that space. Four decimal ASCII digits incl. leading zeros = 10^4 = 10000
  candidates; iterate `f"{n:04d}"`, compute `zlib.crc32(s) & 0xffffffff`.
- Report: target CRC, charset, theoretical space, ACTUAL attempts, hit
  uniqueness (multiple hits need extra constraints). Verify hit by recompute.

## CRC32 inversion (given CRC + declared length ⇒ content) — the reverse problem
- For a FIXED length, CRC32 is an affine map over GF(2). With the length
  known (declared field, e.g. a ZIP entry's usize): 1–3-byte inputs are
  uniquely invertible (injective) and exactly 4 bytes is a bijection — ONE
  solution; >4 bytes has no unique solution, do not treat it as invertible.
- Wrong length ⇒ "collision preimage": matches the CRC but is not the
  original content. Use the declared length, never a guessed one.
- Solve with GF(2) Gaussian elimination (columns f(2^i)⊕f(0)) — instant, no
  enumeration; then DOUBLE-verify: recompute CRC AND a structural check
  (inflate / re-CRC / readable text). Tampered or corrupted CRCs usually
  yield preimages that fail the structural check — report failure, do not
  ship the garbage.

## Nested streams — per-layer signature identification
- Each layer: record signature / type / size / SHA-256, then decompress the
  next layer. NEVER choose a decompressor by extension (.gz content can be
  bzip2, etc.).
- Signature cheat-sheet: gzip `1f 8b 08`, bzip2 `BZh`, zlib `78 9c/da/01`,
  raw deflate (no header), ZIP `PK\x03\x04`, PNG `89 50 4e 47`.
- Try order when signature is ambiguous: gzip → bz2 → zlib(15) → raw(-15).

## Split-volume ZIP reassembly
- Concatenate volumes in part-number order: `.z01` first, `.zip` (last
  volume) last. The Central Directory and EOCD live in the LAST volume and
  their offsets are relative to the FULL concatenated file — parsing the last
  volume standalone shows `cd_offset` beyond EOF, which is itself the tell.
- After concatenation verify: EOCD end == file end, CD end == EOCD start,
  entry count matches, every member CRC recomputed and matched, and record the
  reassembled file's SHA-256.

## Encryption classification BEFORE any password/key operation
- Traditional ZipCrypto: bit 0 set + method 0/8/12 + no strong-encryption bit
  (bit 6). AES ZIPs: method 99 and/or bit 6 — do NOT treat as ZipCrypto.
- Weak-password: only the provided small dictionary, each candidate at most
  once; record entry count and attempt order. `zipfile.ZipFile.read(name,
  pwd=...)` raises RuntimeError("Bad password") per wrong candidate.
  Never write the recovered password to long-term memory.
- Structured attacks come BEFORE dictionaries: if known-plaintext material
  exists (public text, unencrypted twin, fixed headers; ≥12 known bytes with
  ≥8 contiguous), skip the dictionary and go to the bkcrack workflow above.
  Any dictionary run gets a hard budget (time or candidate cap); a full
  wordlist returning 0 hits means "return to structure", not "widen the
  list".

## bkcrack known-plaintext workflow (traditional ZipCrypto only)
- bkcrack 1.8.1 is a Windows-native exe (no cygwin dll). Stage from the
  read-only tool pool: verify source SHA-256 against the expected value, copy,
  re-verify, and re-verify after running.
- Preconditions: cipher member and plaintext member have the SAME name,
  uncompressed size, CRC, and compression method — confirm both archives with
  `bkcrack -L`.
- Workflow:
  1. `bkcrack -L <cipher.zip>` — confirm members are ZipCrypto.
  2. `bkcrack -C <cipher.zip> -c <member> -P <plain.zip> -p <member>` — recover
     internal keys (output: `Keys: k0 k1 k2`).
  3. `bkcrack -C <cipher.zip> -k k0 k1 k2 -D <out.zip>` — passwordless copy.
  4. Verify: flag_bits cleared (0x0000), CRC correct, content readable; as an
     independent check, compare the decrypted known member byte-for-byte with
     the plaintext source.
- Do NOT recover the original password, do NOT convert to password brute
  force, keep internal keys only in report/work.
- Key-state reuse across archives: the recovered keys are an internal STATE,
  not the password — archives encrypted with the SAME password share the same
  keystream start, so keys recovered from one archive decrypt the other (a
  different password fails ⇒ free negative control). A "same password" hint ⇒
  test cross-archive reuse first.
- Phase semantics (confirmed empirically): the recovered state applies at the
  START of the encrypted data region, with the 12-byte header still ahead —
  so decrypt the region from byte 0; output[0:12] is the header region
  (random-looking bytes are NORMAL) and the real content starts at offset 12.
  Seeking to offset 12 with the unadvanced state decrypts with the wrong
  phase (garbage). Judge success by structure (inflate / CRC / readable
  text), never by "the first bytes look like garbage".
- Standard keystream byte formula: `((key2 | 2) * ((key2 | 2) ^ 1) >> 8) &
  0xFF`. A sample or writeup using `|3` is a nonstandard variant (same value
  when key2's low bit is set) — implement the standard form and compare.

## raw DEFLATE vs wrappers
- Three shapes: zlib wrapper (`78 xx` header + adler32 trailer), gzip wrapper
  (`1f 8b` header + crc32/isize trailer), raw DEFLATE (no header/trailer).
- Diagnosis: `zlib.decompress(data)` fails with `incorrect header check`
  (expects a zlib wrapper) while `zlib.decompress(data, -15)` (raw) succeeds
  ⇒ raw DEFLATE. Record BOTH outcomes, plus first-byte check (`78 9c/da/01`?
  `1f 8b`? neither?).
- A ZIP member with method 8 whose content is itself a raw deflate stream:
  first unzip (which unwraps the zip's own deflate), then raw-decompress the
  member content with wbits=-15.
- Segmented / per-chunk deflate: a payload may be a SERIES of independent raw
  deflate streams (each with its own block header/BFINAL, no shared wrapper).
  A whole-stream inflate failure does NOT rule this out — cut chunks by their
  DECLARED lengths (entry sizes), inflate each with wbits=-15, concatenate;
  zero padding after a chunk's final block is tolerated. Treat whole-stream
  and per-chunk as two models and switch after ~3 failures of one; decide by
  block-structure evidence.

## Timestamp fields (DOS vs 0x5455 Extended Timestamp)
- DOS datetime (LH and CD each carry one): LOCAL time, no timezone, 2-second
  resolution; decode bits: time = h(5)/m(6)/s(5)*2, date = y(7)+1980/m(4)/d(5).
- 0x5455 Extended Timestamp (extra field, LH and CD): UTC; flags bits select
  mtime(bit0)/atime(bit2)/ctime(bit3), each a 4-byte LE unix time.
- Layout ambiguity: 0x5455 can be written with a 1-byte size (Info-ZIP style:
  tag 55 54, size, flags, times) or the generic 2-byte data-size layout.
  Resolve by self-consistency: pick the reading where the field consumes the
  extra field exactly (no stray bytes), flags agree with present data, and the
  resulting mtime is plausible (e.g. equals the corpus creation date). Report
  the ambiguity when present — "timestamps need field context" is often the
  point.
- A DOS/0x5455 conflict proves only metadata inconsistency; it cannot alone
  prove a tamperer, a tool, or the real event time.

## Recurring script pitfalls (bit this session, again)
- Python f-strings cannot contain backslashes: hoist `b'PK\x05\x06'`-style
  byte patterns and escaped quotes into named variables before f-string use.
- In terminal one-liners, `x & 1` bit tests are misparsed as shell
  backgrounding (`&`): use `x % 2` instead.
- Cygwin binaries (npiet) cannot resolve MSYS-relative paths — pass absolute
  `D:/...` Windows paths; they print a harmless `nodosfilewarning`.
