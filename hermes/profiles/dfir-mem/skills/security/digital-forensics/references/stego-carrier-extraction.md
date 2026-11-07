# Stego carriers and hidden text: extraction recipes

Concrete, validated recipes from a GIF-heavy stego training session (2026-08-26). Pair with the
"Embedded payloads, stego carriers, and hidden text" section of SKILL.md.

## 1. GIF GCT/palette LSB payload extraction

Validated end-to-end on a GIF87a sample. The message lived directly in the LSBs of the first
palette bytes — no encryption, no reordering.

1. **Parse the header fields first.**
   - Bytes 0-5: signature (`GIF87a`/`GIF89a`).
   - Logical Screen Descriptor = bytes 6-12: width LE @6, height LE @8, **packed byte @10**:
     bit7 = GCT flag, bits 4-6 = color resolution, low 3 bits = Size of GCT field.
   - GCT entries = `2 ^ (size_field + 1)`; GCT starts at offset **13** (6-byte header + 7-byte LSD);
     size = entries × 3 bytes. For 256 entries: 768 bytes.
   - Pitfall: byte @11 is the **background color index**, NOT part of the packed field — one
     independent implementation initially read size from @11 and failed its own assertion. That
     failure is the cross-check working; fix and re-compare.
2. **Collect one bit per carrier byte, in file order:** `bit = byte & 1` for every byte of the GCT
   (each byte is one R/G/B component of one palette entry — walk them as raw bytes, not per entry).
3. **Do NOT compute a delta/XOR against any baseline** (theoretical palette formula, "clean"
   reference, or pixel-index mapping). The delta = message ⊕ baseline stream = mixed noise.
   In the validating session, ~60 encoding variants over the XOR mask (channel subsets, MSB/LSB,
   bit reversal, sign, masks, barcode/bitplane visualizations) produced nothing; direct `& 1`
   reads recovered the flag on the first try. The ~130 "flipped" bytes observed were simply the
   message region (248 bits ≈ half flipped, consistent with ASCII text).
4. **Pack MSB-first**: the first collected bit is the MSB of the first output byte; 8 bits per byte.
5. **Length field**: first 16 bits, big-endian → payload length (e.g. `0x001D` = 29).
6. **Payload**: the next `length` bytes. Report length field, payload hex, and decoded string
   verbatim (preserve case; do not normalize).
7. **Two independent implementations, no shared extraction function**:
   - impl A (bit ops): `bits = [b & 1 for b in gct]`, pack with shifts;
   - impl B (string): `"".join(format(b, '08b')[-1] for b in gct)`, then `int(chunk, 2)` per 8 chars.
   Outputs must match byte-for-byte.
8. **Prove the message region**: the untouched tail of the packed bitstream should equal the
   theoretical carrier LSB stream bit-for-bit (in the session: GCT bytes 248..767 produced a
   repeating `e38e38e3…` cycle that matched the palette formula `(i, 5i mod 256, 255-i)` LSBs
   exactly). That match proves only the first 248 carrier bytes' LSBs were modified.

## 2. Low-contrast / anti-aliased text in dithered image frames

Symptom: a GIF's frames contain text, but extracting pixels by the single most-frequent
"text" palette index yields only a handful of stray pixels, and OCR reads nothing or garbage.

- **Why**: text is anti-aliased into a dithered background, so its pixels spread across several
  adjacent palette indices (e.g. 53/96/139 = text + AA shades, against 8+ dither indices).
  The single-index mask captures only the core pixels.
- **Fix — luminance threshold reconstruction**: per frame, sum R+G+B per pixel and threshold
  between background and text luminance (e.g. `> 300` for light text on a dark dithered
  background; invert the comparison for dark text on a light background). Render the thresholded
  mask, then run OCR or read glyphs from the clean mask.
- OCR on the thresholded mask is far more reliable than OCR on the raw low-contrast frame
  (raw-frame OCR dropped trailing underscores and read words only partially).

## 3. OCR limitations on isolated glyphs (Windows WinRT OCR observations)

- A lone `}` produced **no output at all** — even at 20× upscale on a pure black-and-white mask.
- `frames_` was read as `frameS` (the `s_` merged into a capital S).
- Trailing underscores were dropped from `frames_`, `restore_`; a standalone `gif_` (with
  underscore) was read correctly only after thresholding.
- Conclusion: treat OCR on isolated punctuation as unreliable; verify glyph identity against
  pixels, not OCR.

## 4. Objective glyph identification: reference template matching (Dice)

When OCR is unusable and the glyph is a single character, render reference glyphs with a system
font (e.g. `C:/Windows/Fonts/arialbd.ttf`, 24px), threshold to binary, trim to bounding box, and
compute Dice overlap against the unknown glyph mask:

```
inter / union  where both masks are padded to the same bbox
```

Validated scores (unknown glyph = frame 5 of a 6-frame GIF):

| reference | Dice |
|---|---|
| `}` | 0.562 |
| mirror(`{`) = `}` | 0.674 |
| `{` | 0.316 |
| `S` | 0.156 |
| `s` | 0.175 |

The `S`/`s` scores were under a third of the `}` score — decisive. Note the skeleton argument too:
braces have a continuous straight spine plus top/bottom hooks; `S` has no straight spine.
Pixel height is NOT character-category evidence — `{}()[]|` occupy full cap height like capitals,
so height only separates lowercase from full-height glyphs, never letter from punctuation.

## 5. Fragment assembly rule

Multi-frame text puzzles: concatenate fragments in their declared order (frame order / header
numbering). If separators (`_`, `-`) are already present inside the fragments, do NOT add them by
convention — assemble exactly what the pixels/OCR show, then compare against the expected
`flag{...}` wrapper only as a closure check (the final frame is usually the closing brace).
