# Day 6 — Audio steganography techniques (SecurityLab bootcamp, 2026-08-27)

> **⚠ Some sections superseded by later teacher reviews — see
> `day6-teacher-corrections.md` (round 1) and `day6-round2-corrections.md`
> (round 2, structural anchors).** In particular: the "AM sideband
> identification" section below is INVALID for the T2 sample (the equally
> spaced peaks were DFT frequency-ROW spacing, not modulation sidebands); the
> SSTV "1100=0, 1300=1" VIS mapping can be inverted (this sample: 1100=1,
> 1300=0 → VIS 44); the SSTV "Martin M2 / 255+1 partial line" conclusion was
> wrong (Martin M1, 256 lines, exact division); and SSTV luminance is
> **1500 Hz = black, 2300 Hz = white**. Read the corrections before applying
> these recipes.

6 unknown benign audio samples; worked methods below. Sample-specific values stay
in the day-6 report; this file keeps the reusable recipes and the working
numerical patterns that recur across audio-stego classes.

## Audio inventory (do this first)
- RIFF/WAV: parse chunks (fmt/data), verify `wave.open` OK, record channels/rate/
  bits/duration. Check for EXTRA chunks, trailing bytes after the last chunk,
  and LSB statistics (ones ratio ~0.5 = random, consistent with encrypted
  embedding; a deviating ratio suggests plaintext LSB payload).
- MP3: verify real MPEG frames (frame sync walk, layer/bitrate/channel count)
  before assuming any MP3-specific tool applies. A "MP3Stego" question requires
  a real MP3, not a renamed file.
- Audio `file` type is auxiliary only — never proof of the stego scheme.

## Morse timing (envelope → durations → base unit)
- Envelope: short-window mean or |hilbert|; binarize at ~0.25×max; take on/off runs.
- Histogram the on/off durations and CLUSTER into units: dot ≈ 1u, dash ≈ 3u,
  symbol gap ≈ 1u, char gap ≈ 3u, word gap ≈ 7u. No 7u gaps ⇒ no word breaks.
- Classify on-runs by threshold (e.g. ≤2u = dot); decode; then apply the output
  chain (hex→ASCII etc.) and validate the result reads as text.

## Channel arithmetic & anti-phase separation (stereo)
- Always compute L, R, L+R, L−R (RMS and spectrograms). Equal channel RMS with
  **L−R ≫ L+R ⇒ anti-phase dominant**: L = C+X, R = C−X, where C=(L+R)/2 is the
  common-mode signal and X=(L−R)/2 is the differential signal.
- Separate the two modes and analyze each: the carrier lives in one mode, the
  hidden/modulated content in the other. Spectrogram text must be supported by
  BOTH the channel arithmetic and numeric energy — a rendering alone is not proof.

## AM sideband identification
- Equally spaced peaks at f_c ± d, f_c ± 2d, … around a carrier ⇒ the carrier is
  AM-modulated by a signal of rate d. Verify EVERY peak against f_c ± n·d before
  concluding. The comb spacing = the modulation frequency.
- If the band below the carrier is ~40 dB quieter, there is no true fundamental
  there — the main band IS the signal, don't hunt for a hidden lower tone.

## DTMF
- Self-written Goertzel per segment (low group + high group) → digits; then
  verify with an independent tool (dtmf2num.exe) — outputs must match digit for
  digit. Document the post-digit grouping chain (e.g. 3 digits per ASCII code).

## SSTV structure (no virtual sound card / no GUI)
- VIS decode: 1900 Hz leader → 1200 Hz start (~30 ms) → 8×30 ms data bits
  (1100=0, 1300=1; 7 bits + parity) → 1200 Hz stop. Decode at SEVERAL window
  alignments; a stable bit pattern across alignments is the real VIS. Check parity.
  A non-standard VIS value (e.g. 83, absent from MMSSTV's mode table) is possible
  in training samples — identify the mode from the LINE STRUCTURE instead.
- Line sync: **matched filter** (correlate with a 1200 Hz burst template) beats
  per-window threshold/zero-crossing detection, which misses most syncs.
  Line period = median sync gap; pixel rate = data duration / pixels per line
  (Martin M2 ≈ 320 px @ 1.366 ms/px; Martin M1 ≈ 0.898 s/line).
- Same-image check: correlate first-half vs second-half rows; low correlation ⇒
  single image, not a repeated transmission.
- Demodulate with BOTH 320 px and 640 px line widths; small noisy glyphs may be
  legible in the wider version. Glyph segmentation fails when strokes touch;
  template matching needs real column gaps — if neither works, report the
  structure and the next validation step honestly.

## MP3Stego (Decode.exe workflow)
- `Decode.exe -X -P <pass> <file.mp3>` writes `<file>.pcm` and `<file>.txt`.
- Wrong password prints `[ERROR] Encrypt: unexpected end of cipher message` but
  EXIT CODE IS 0 — read the error line, not the exit code. Success prints
  "Decoding … is finished" and the output names.
- Dictionary discipline: one attempt per candidate, in order; record attempt
  count; no rockyou/masks.

## DeepSound via runtime API (no GUI needed)
- DeepSound 2.x is a .NET 4.8 app; `Steganography.dll` is **x86** — load it in
  32-bit PowerShell (`C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe`);
  64-bit PowerShell throws BadImageFormatException.
- `Coder.decodeQualityMode` is a PRIVATE FIELD behind a read-only property —
  set it via reflection (BindingFlags NonPublic,Instance). Its value gates
  `DecodeData`: the method computes `length / decodeQualityMode` internally, so
  an unset field = divide-by-zero which the DLL wraps into the misleading
  "Input parameter 'length' must be even number". Root cause found by
  disassembling the IL (see scripts/il_disasm.py).
- `DecodeData(byte[] pcm, int len)` with NormalQuality mode returns the
  decrypted container header: magic `DSC2` (DeepSound Container v2) + encrypted
  payload. Rest of the extraction (file table, AES decrypt) lives in
  `DecodeFilesFromWav` — GUI or a fully initialized Coder; if the init path
  NREs, say so and hand the next step to the user.
- Carrier sanity: a pure fmt+data WAV with random LSBs and no plaintext strings
  is consistent with an encrypted embed — don't call it "no stego" on those
  grounds alone.

## Locked-session GUI limits (Windows)
- When the desktop session is locked (LockApp present): background input
  injection is refused as "occluded by another window", and foreground
  activation fails ("Windows did not activate exact target HWND"). GUI stego
  tools (MMSSTV, DeepSound) become undrivable. Disclose the blocker and pivot
  to the runtime API / self-written parser; give the unlock-and-retry step.

## Vision-model hallucination on noisy glyphs
- Auxiliary vision models CONFIDENTLY read text that is not there: on SSTV
  noise it produced "SSTV", "2345", "Testcard", even Korean text — different
  readings on the same crop. NEVER let a vision model's character reading be the
  evidence; treat it as a lead only and confirm with deterministic rendering
  (binarized ASCII at full resolution, or template matching). If deterministic
  reading fails too, report the glyph structure, not the hallucinated string.
