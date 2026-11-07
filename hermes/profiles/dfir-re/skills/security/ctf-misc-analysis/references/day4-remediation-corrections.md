# Day 4 remediation corrections (SecurityLab, 2026-08-26)

Teacher-corrected recipes that supersede the first-round notes in
`day3-day4-techniques.md`. Session-specific values from one training corpus;
reuse the STRUCTURE, not the numbers.

## Piet strip program — corrected block accounting and execution boundary

First-round analysis misread the strip as "26 pastel blocks + 26 saturated
separators" and ran npiet with a self-chosen `-e 20000` limit, accepting 200
repeated outputs. Teacher correction (validated end-to-end):

1. **Classify colors against the CANONICAL Piet sets**, not heuristic rules:
   - light = {(255,192,192), (255,255,192), (192,255,192), (192,255,255),
     (192,192,255), (255,192,255)} — note light red has ONE 255 channel;
   - saturated = {(255,0,0), (255,255,0), (0,255,0), (0,255,255), (0,0,255),
     (255,0,255)} — note yellow has TWO 255 channels;
   - black = (0,0,0).
   A classifier built as "two 255 channels + one 192" mislabels 4 of the 6
   light colors and yellow; hardcode the sets.
2. **Structure**: N light blocks (ASCII payload, width/codel = value) + N
   saturated blocks (push) + 1 pre-termination light block (pushes a final
   small value, e.g. width 2 → value 1) + 1 black boundary block =
   (2N+2) runs = (2N+1) colored + 1 black. For N=25: 52 runs = 51 colored
   + 1 black. The first 2N operations are N push + N out(char) = the answer.
   **The pre-termination block is NOT an answer character** — a parser that
   includes it appends a spurious `\x01` (first-round bug).
3. **Execution boundary**: when the task/evidence gives an explicit step
   limit (Execution-Step-Limit = 50), use exactly that:
   `npiet -q -cs 2 -e 50 <file>`. With the correct limit the answer appears
   in stdout exactly once (25 bytes for N=25). A larger self-chosen limit
   (`-e 20000`) is NOT equivalent — it redefines "when the program ends",
   and the loop tail produces repeated identical output you then rationalize.
   Record the step-limit message truthfully:
   - npiet v1.3 prints `error: configured execution steps exceeded (N steps)`
     to **stderr** but its **exit code is 0** — record both facts.
   - stdout and exit info go in separate files.
4. **Cygwin path quirk**: npiet.exe (Cygwin) cannot resolve MSYS-relative
   paths like `../../work/...` ("cannot open ... No such file or directory");
   pass an absolute Windows path `D:/...` (it prints a `nodosfilewarning`
   notice — harmless).

## Similar image halves — even/odd column de-interleaving, not "duplication"

First-round analysis concluded "two independent copies of the text, dedupe to
one copy" (202×90 crop). Teacher correction (validated end-to-end):

- Forward model: `current[:, 0:250] = original[:, 0::2]` (left half = even
  columns), `current[:, 250:500] = original[:, 1::2]` (right half = odd
  columns). The columns were SPLIT and reordered, not duplicated.
- Inverse (full-size, no cropping):
  ```python
  restored = np.empty_like(current)
  restored[:, 0::2] = current[:, 0:250]   # even cols ← left half
  restored[:, 1::2] = current[:, 250:500] # odd cols ← right half
  ```
  Restored image is the original dimensions (500×90); hash it.
- **Round-trip validation**: `roundtrip = np.concatenate([restored[:,0::2],
  restored[:,1::2]], axis=1)` must be pixel-identical to the original
  (diff count 0). Then confirm the restored image renders ONE full-width text
  copy (text column span ≈ chars × normal char width — e.g. 403 px for 29
  chars at 500×90), readable as the flag.
- **Why the halves look ~identical**: adjacent even/odd columns are naturally
  near-identical in background and glyph interiors (94.20% identical pixels
  in the validating sample); differences concentrate at glyph edges.
  High similarity is EXPECTED under splitting — it only raises the candidate,
  it does not prove duplication. Test copy vs split candidates side by side;
  round-trip + restored readability decide.
- **Pitfall**: checking `left_half == current[:, 0::2]` against the sample
  itself proves nothing (current's left half is not current's own even
  columns — the model relates current to the UNKNOWN original). The
  round-trip is a consistency check of the inverse implementation, not a
  proof of the forward model; the readability of the restored image is the
  independent confirmation.
