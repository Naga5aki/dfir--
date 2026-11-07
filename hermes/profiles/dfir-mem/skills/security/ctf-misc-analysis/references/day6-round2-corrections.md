# Day 6 round-2 corrections — structural anchors override round-1 (2026-08-27)

Second teacher review (75/100) invalidated several round-1 conclusions. These
deltas OVERRIDE the corresponding sections of `day6-teacher-corrections.md` and
`day6-audio-techniques.md`. Method that replaced blind parameter tuning:
**structural anchors** — the teacher supplies sample counts, matrix sizes,
protocol field values, and HASHES of the expected decode output. Use them as
gates: Gate 0..N, only advance when the current gate's assertions all pass;
on any anchor mismatch STOP text reading and report first mismatched variable,
actual vs expected value, and earliest code location producing it.

## 1. Spectrogram-text matrix (T2) — the correct structure

Round-1 "60 ms columns / N=720 / 14×255 matrix" was WRONG. The correct
structure (verified by teacher hash):

- Column = fixed SAMPLE COUNT with zero remainder: `len(diff) == 420 × 438`
  exactly (35 ms columns @ 12 kHz). Verify by slicing — do not derive column
  width from change-point/boundary detection on a coarse peak track (that is
  how 60 ms was hallucinated from ~1760-sample runs).
- Frequency rows sit ON the N-point DFT bins: `frequency[row] = (25 + 4·row) ·
  sr / 420`, row = 0..35 → 36 rows, spacing = **4 DFT bins**. The ~114 Hz
  spacing here is the FREQUENCY-AXIS ROW INTERVAL, **not an AM modulation
  frequency** — this exact trap was hit twice (round 1: "114.3 Hz AM
  sidebands"; round 2 fixed it with the anchor).
- Energy matrix E (36, 438), rows low→high freq, cols left→right time.
- Implementation A: Goertzel per (column, anchored frequency). Implementation B:
  per-column FFT reading the EXACT DFT bins `25+4r` — no zero-padding, no
  arbitrary peak search.
- Binarize: `B[:, col] = E[:, col] > 0.45 * max(E[:, col])` — STRICT `>`,
  not `>=`; a column whose max is below an explicitly logged noise floor is
  all-zero. B must be uint8, C-order, values only 0/1.
- **Each implementation must hit the teacher-provided hash of
  `B.tobytes()` independently.** Two implementations that only agree with EACH
  OTHER are not validated — a shared wrong structure (same bad column width,
  same bad row mapping) makes both agree while both are wrong.
- Only after the hash matches: render `B*255` PNG (no interpolation), read the
  text character-by-character from the matrix with an anchored grid. Distinguish
  near-identical words glyph-by-glyph (spectrum vs spectrogram — the round-1
  wrong matrix rendered a phrase ending in the wrong word).

## 2. SSTV (T4) — mode, cursor, mapping, channels

- **VIS bit-frequency mapping can be INVERTED**: this sample maps
  1100 Hz=1, 1300 Hz=0 (opposite of the usual table). Always measure the tone→
  bit assignment empirically (band energies per 30 ms bit window) and
  cross-validate: parity (even, 4 ones incl. parity), LSB-first value, and the
  mode table. Round-1 decoded the same tones as `1,1,0,0,1,0,1` = 83; the
  correct `0,0,1,1,0,1,0` = **44 = Martin M1**. Round-1's "non-standard VIS 83,
  identify mode from line structure" was the wrong lesson — the VIS was
  standard once the mapping was flipped.
- **Fixed protocol cursor beats per-line sync re-search.** Line =
  sync(233) + porch(27) + 3×(7029+27) = 21428 pts @ 48 kHz (Martin M1, 320×256,
  color scan order G,B,R). Advance the cursor by sample count from sample 43680
  for 256 lines and ASSERT the final cursor equals the total sample count
  (5529248). Do NOT re-search each line's sync (round-1 re-detection caught the
  VIS start tone as a "sync", producing a phantom "255 complete + 1 truncated
  line" — in fact 5529248 = 256×21428 exactly, no truncation at all).
- **Luminance: 1500 Hz = black (0), 2300 Hz = white (255).** The inverted
  mapping was a graded error.
- Output channel permutation: signal scan order is G,B,R; writing into a
  standard [R,G,B] (256,320,3) array means G→ch1, B→ch2, R→ch0. When a
  teacher hash misses, sweep the 6 permutations + round-vs-truncate in value
  mapping (round() was the hit) before touching anything else.
- Pixel slicing: `start = pixel*7029//320`, `stop = (pixel+1)*7029//320`.
- **Frequency estimation on ~22-sample pixels**: the cosine-autocorrelation
  (LS ratio) form `cos = dot(middle, core[:-2]+core[2:]) / (2·dot(middle,
  middle))`, `f = acos(clip(cos,-1,1))·sr/(2π)` (core = pixel segment minus
  first/last 2 samples; middle = core[1:-1]) is EXACT even on sub-cycle
  windows (< 1 period), where zero-padded FFT and uniform DFT-grid peaks are
  PHASE-BIASED (measured 2190 Hz → 1847/2360 depending on phase). A full
  3-param LS sine fit over a 1 Hz grid gets close (MAE 0.93) but mislocks on
  sub-cycle windows (max AE 75); the 2-param (no DC) fit is closer to the
  teacher's model.
- Independent second implementation that EXACTLY matched the teacher hash:
  per-sample phase ratios `arccos((x[n-1]+x[n+1])/(2·x[n]))` then **median**
  over the window's samples → frequency. Different algorithm, identical output
  (MAE 0, max 0).
- Restored image should contain: top color bars (4), border, an English mode
  label, and the text lines. Vision model readings on the restored image were
  only auxiliary — deterministic per-glyph reading won.

## 3. Reporting / memory discipline (repeated across both correction rounds)

- Keep ALL historical errors in the original reports with prominent
  "invalidated" banners; new correction report gets a fixed section structure
  (Teacher Recheck → Invalidated Claims → Structural Gates → Reproduction →
  Independent Validation → Corrected Result → Root Cause → Evidence Integrity →
  Memory Corrections).
- One-time parameters (sample counts, matrix dims, VIS values, segment point
  counts, teacher hashes, passwords, flags) NEVER go into long-term memory —
  scan for them and genericize; only cross-sample methods are stored.
