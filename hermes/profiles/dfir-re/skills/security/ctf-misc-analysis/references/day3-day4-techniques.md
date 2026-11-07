# Day 3–4 Bootcamp Recipes (SecurityLab, 2026-08-26)

Session-specific detail behind the `ctf-misc-analysis` patterns. Values are from one
training corpus; reuse the STRUCTURE, not the numbers.

## GIF palette (GCT) LSB extraction — the direct-read algorithm

Sample: GIF87a 64×64, 256-entry GCT at file offset 13 (768 bytes).

1. Verify GCT from the Logical Screen Descriptor: packed byte at offset 10 —
   bit7 = GCT flag, low 3 bits = Size of GCT → entries = 2^(n+1). **Pitfall:
   offset 11 is the background-color index, not the size field** (off-by-one
   that a dual-implementation check caught).
2. Walk the GCT's raw RGB bytes in file order; take `byte & 1` per byte.
3. Pack MSB-first (first collected bit = MSB of first byte) → 768 bits = 96 bytes.
4. First 16 bits = big-endian payload length; read that many bytes.
5. Cross-check: the untouched trailing region's LSB stream must equal the
   theoretical palette formula's LSB stream (here `e3 8e 38 …` for
   (i, 5i mod 256, 255-i) on bytes 248..767) — proves only the message region
   was modified.
6. Two independent implementations: bit-ops (`b & 1` + shift-pack) vs
   string-based (`format(b,'08b')[-1]` then `int(chunk,2)`) — no shared
   extraction function.

Key lesson: XOR'ing the palette against the theoretical formula gives
message⊕formula noise, NOT the message. Read the carrier bits directly.

## JPEG trailing container

Marker walk (skip `FF` fill bytes; SOS → scan entropy to next marker) finds the
EOI (`FF D9`). Trailing data = everything after EOI+2. Verify the ZIP triple:
Local Header (method/crc/csize/usize/name), Central Directory (consistent),
EOCD (entries/cd_size/cd_offset; EOCD end == file end).

**ZIP header CRC = CRC32 of the UNCOMPRESSED data.** A self-written check that
CRC's the compressed stream reports a false mismatch — recompute on inflated
bytes or use `zipfile`.

## Firmware-style segment container (SLFW-like)

Header: magic(4) + version(2, LE) + count(2, LE); descriptor table 16 B/entry:
tag(4) + offset(4, LE) + length(4, LE) + crc(4, LE). Parse every descriptor;
recompute crc32(segment) vs stored; pairwise overlap check; off+len bounds;
inspect table→first-segment gap and the file tail. Cut by table offsets.
Cross-format segments (PNG image + gzip text) may each carry part of the answer
— concatenate in table order.

## Dual-image diff

Per-channel: count differing pixels and collect the value set. Real overlay =
single channel, constant delta (e.g. R +60 on 2679 px), zero diffs elsewhere;
compression noise = all channels, scattered values. Outside the mask the two
images must be identical. Enhance with |D|×K saturation or binarize the mask
(white-on-black) before OCR.

## Piet strip program

5444×2 PNG, both rows pixel-identical → one-line program, codel size 2.
52 color runs = 26 pastel (light hue) blocks + 26 saturated 2-px separators.
Block width / 2 = codel count = pushed value. Hue sequence descending by 1
(red→magenta→blue→cyan→green→yellow) makes the saturated→next-pastel transition
(5,−1) = out(char). So: flag chars = each pastel block's width ÷ codel size.
Run npiet with `-cs 2 -e <limit>`; stdout and the "execution steps exceeded"
exit message in separate files; the program loops, so the same answer repeats —
count it once. Last 2-px block pushes 1 (invisible \x01) — a loop artifact, not
part of the answer. Always: verify npiet SHA against expected, run `-h` and a
benign black/white image test before the real program.

## Shard reassembly (SLP1-like)

Per piece: magic(4) + index(1) + total(3, LE) + payload_len(4, LE) + crc(4, LE)
+ payload. Sort by EMBEDDED index, not filename (here B(0)→D(1)→A(2)→C(3)).
Verify 4/4 CRCs, index set completeness, then full-structure validation of the
reassembled file (PNG signature, IHDR/IDAT/IEND walk with CRC, IEND end == EOF).

## Text glyph identification (OCR limits)

- Luminance threshold (R+G+B > bg+margin) reconstructs anti-aliased glyphs that
  exact palette-index extraction misses (7 stray pixels vs full glyph).
- Template matching: render reference glyphs (Arial Bold) and compute Dice
  overlap — brace vs letter scores separated decisively (0.56–0.67 vs 0.16).
- OCR behaviors: isolated `}` unreadable even at 20× B&W; `s_` merged into `S`;
  trailing underscores dropped; `o`/`0` confusion. Pixel-height is not
  character-category evidence (punctuation is full cap height).
- Pixel-column duplication: locate copies + gaps (gaps must be pure bg),
  per-column dy histogram ≈ 0 with edge-scattered diffs ⇒ rendering variation,
  not a column permutation; deduplicate to one copy as the repaired image.
