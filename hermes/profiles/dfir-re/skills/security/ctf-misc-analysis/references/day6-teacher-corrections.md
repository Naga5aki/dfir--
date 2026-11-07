# Day 6 teacher corrections — audio stego evidence boundaries (2026-08-27)

> **⚠ SUPERSEDED IN PART by the second teacher review (75/100) — see
> `day6-round2-corrections.md`.** Specifically invalidated below:
> §1 step 3 "60 ms columns → N=720 ↔ 16.67 Hz spacing" (real: 420-sample
> columns × 438, frequency rows on DFT bins, spacing = 4 bins and is NOT a
> modulation rate); §1 step 7 "matrices must agree with each other" (each
> implementation must hit an independent teacher hash instead); §2 "VIS
> 1100=0/1300=1" (mapping can be inverted — this sample: 1100=1/1300=0 → 44);
> §2 "Martin M2 confirmed / 255 complete + 1 partial trailing line" (real:
> Martin M1, 256 lines, total samples ÷ line = 0, no truncation — the phantom
> partial line came from re-detecting the VIS start tone as a sync);
> §2 "1500 Hz = white" (real: 1500 Hz = black, 2300 Hz = white);
> §2 Goertzel-vs-FFT-peak dual (FFT peak is phase-biased on sub-cycle pixel
> windows; cosine-autocorrelation + per-sample-phase-median both hit the
> teacher hash exactly).

Teacher review of the first Day 6 round (3/6 solved, 78/100) corrected three
over-claims and one dead-end. These deltas OVERRIDE the corresponding sections
of `day6-audio-techniques.md` (which still carries the pre-correction text for
the AM section and the DeepSound dead-end).

## 1. Frequency-peak evidence boundary (T2: stereo channel-difference text)
- Symmetric / equally spaced peaks (f_c ± d, f_c ± 2d, …) form an **AM
  CANDIDATE only — not proof of AM modulation**. A graded error was writing
  "2200 Hz carrier AM-modulated at 114.3 Hz (sidebands verified)" from a
  comb alone. Correct modeling: discrete multi-frequency energy per fixed
  time column.
- Mandated workflow (all steps were required):
  1. sum/diff in **int32** (int16 overflows and destroys the separation).
  2. Three-window numeric comparison: low-frequency common component lives in
     sum; hidden multi-frequency content lives in diff — consistent across
     several time windows.
  3. Column-width DUAL estimation, both must agree: (a) mode of adjacent-column
     change-point gaps → N = sr·col; (b) base spacing Δf of the discrete peak
     set → N ≈ sr/Δf. (Worked example: 60 ms columns → N=720 ↔ 16.67 Hz
     spacing → N=720.)
  4. Per-column whole-window discrete-frequency energy (rectangular window).
  5. energy[frequency_row, time_column] matrix; binarize with threshold
     **relative to that column's max** (0.3×colmax), not a global threshold.
  6. Render all four orientations; pick the readable one.
  7. Dual implementation (Goertzel vs FFT at same bins): binary matrices must
     be element-wise identical — report 0 diff or the differing coordinates
     with cause (power vs magnitude units was the trap: sqrt the Goertzel
     power before comparing with FFT magnitude).
  8. Read text from the matrix with an anchored character grid (advance
     px/char measured from underscore bars / word spans), verifying each
     glyph window directly. Vision/OCR auxiliary only.
- The recovered text is then the flag; the trailing edge of the matrix may
  truncate the last glyph (report the boundary).

## 2. SSTV VIS cross-validation (T4)
- VIS frame must be relocated from the WAV START segment by segment:
  leader(1900, 300 ms) → break(1200, 10 ms) → leader(1900, 300 ms) →
  start(1200, 30 ms) → 8×30 ms bits (1100=0 / 1300=1, LSB-first, 7 data +
  1 parity, even parity) → stop(1200, 30 ms). Per-bit output: sample range,
  estimated frequency, decided value, confidence. Use Goertzel on 10–30 ms
  windows — a 1 ms FFT window (48 samples) has ~1000 Hz bins and cannot
  separate 1100/1200/1300.
- **VIS must be cross-validated against the standard mode table**: if the
  VIS's mode contradicts measured line duration / color-segment count /
  channel order, the VIS decode counts as FAILED — report the inconsistency,
  never force-fit. (Trap hit: Martin M2 timing fully confirmed — 320 px @
  1.366 ms/px, 0.446 s/line, 256 lines — but measured VIS 83 ≠ M2's standard
  40. Round-1 asserted M2 without the cross-check.)
- Line sync pitfalls: (a) the 1200 Hz VIS start tone is misdetected as a line
  sync — drop detections before the VIS stop; (b) files may end mid-line —
  the trailing INCOMPLETE line counts (255 complete + 1 partial = 256;
  reporting 255 was a graded error).
- Cursor advance: from the first complete sync after the VIS stop, advance by
  sample count (sync + porch + N px); do not re-search every line.
- Restored image mapping is **1500 Hz = white, 2300 Hz = black** (standard
  SSTV); the inverted formula was a graded error. Save + SHA-256 the image.
- Dual implementation for the restored image (Goertzel grid vs zero-padded FFT
  peak) — report 8-level and binary mismatch (worked: 2.94% / 0.40%).
- Demodulation pitfalls: 4 ms FFT peak tracks of ~1 ms pixels lobe-lock into
  32 ms "holds" — use the ~1.3 ms pixel window for image demod; keep the slow
  track only for tone-level structure (syncs, VIS).
- Reading the text: multi-block layouts separated by dotted vertical columns;
  read each line's full panorama (content spans the whole width, not just the
  left 40%); character advance is variable-width (fit candidate readings by
  letter count vs measured span); last glyph may sit at the right edge.

## 3. DeepSound headless decode — the init order that fixes the NRE (T6)
- Round-1 dead end: "DecodeFilesFromWav NREs → hand to user". The fix is the
  FULL initialization order — `AnalyzeWav()` alone is not enough, the BaseFile
  object must be constructed:
  ```
  $decoder = New-Object Coder
  $decoder.OriginalBaseFile = $wavPath
  $decoder.DecoderFolder    = $outDir
  $decoder.set_KeyUnicode($candidate)
  $decoder.BaseFileInfo = $decoder.AnalyzeWav($wavPath)
  $decoder.BaseFile = New-Object BaseFileInfoItem($wavPath, $decoder.DecodeQualityMode, $decoder.BuffSize)
  $decoder.DecodeFilesFromWav()
  ```
- Per candidate: NEW Coder + empty output dir, one attempt each; wrong-password
  candidates fail earlier (record stage + exception + output count).
- Read the recovered file only (never execute); record path/size/SHA-256.
- Independent verification: fresh Coder + fresh empty dir + same candidate →
  outputs byte-identical (same SHA). (Worked: 36 B file, both runs
  `7b0a6311…`.)
- Remember: `Steganography.dll` is x86 (32-bit PowerShell via SysWOW64), and
  `decodeQualityMode` is a private field behind a read-only property
  (reflection, NonPublic/Instance).
