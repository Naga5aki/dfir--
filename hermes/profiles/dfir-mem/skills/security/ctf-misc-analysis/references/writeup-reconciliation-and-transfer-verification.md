# Writeup reconciliation & transfer validation（解后复盘：WP 对照 + 迁移验证）

Trigger: a training case leaves the blind-solve phase and the writeup (WP) becomes readable ("对照实际路线与 WP / 复现与迁移验证" stage commands). Reports stay in Simplified Chinese; keep the verdict string `Transfer-Validated` literal.

## 1. Fetch & archive the WP
- `web_extract` may be unavailable (backend configured search-only) — fall back to `curl -sS -L -m 45 -o wp.html <url>`; static blog pages need no JS. If the download truncates, check whether the missing tail matters (article body vs footer) before re-fetching, and record received/total bytes.
- Turn the html into text with a stdlib regex pass (drop script/style/nav, block tags → newline, unescape entities). Save raw html + full text + an excerpt of the relevant section as case evidence.

## 2. Route comparison table
Per phase: actual route vs WP route. Classify: parts BOTH got right, our detours, WP omissions/hardcodes/errors.
- WP defect classes worth recording: unnamed tools ("直接用工具尝试"), missing recipe details (operator chain not stated), typography artifacts vs the raw bytes (full-width colon, stray spaces), non-reproducible observations ("shows whitespace when opened in an editor"), missing validation/control steps.
- Compare WP's stated intermediate values byte-level against your own recomputation AFTER normalizing presentation artifacts (full-width ：→ `:`, strip spaces); a true mismatch is a finding, a typographic artifact is not.

## 3. Detour records — fixed six-field format
```
错误判断 / 被忽略的信号 / 形成原因 / 时间损失 / 更快的判断方式 / 下次停止条件
```
- "更快的判断方式" cites ONLY information available at the time (skills, references, file shape). Never fabricate "we should have known this" from the WP's hindsight; state explicitly that the analysis does not use WP content.
- 时间损失: honest estimate range; note that part of a detour's time may still yield useful negative evidence (route exclusions, near-misses).
- 下次停止条件 must be operational and frozen for reuse (e.g. "two consecutive no-new-evidence rounds on one route ⇒ switch"; "near-miss noise counts as the switch signal").
- Minor items (missing shell utility → stdlib substitute, ~30 s) get a one-line note, not the full format.

## 4. Reproduction from raw artifacts
Recompute EVERY WP key conclusion from the original attachment in a script (extract → parse → recompute → format-assert); never copy WP intermediates as if computed. Save script + log; byte-compare with the WP's values.

## 5. Variants (≥3, each genuinely changes a condition)
Change dimensions: key content/length (incl. misalignment vs ciphertext length), answer content/length, compression/encoding MODE, carrier structure & capacity, tool direction (encode with A → decode with B), invocation form (file arg vs stdin), line endings.
- Build as mini-challenges: construct carrier → encode the hidden message → COMPUTE expected values independently → run the full solve chain with assertions. Auto-escalate carrier capacity on encode failure instead of hand-tuning.
- Every variant gets cross-implementation verification; a bit-sensitive decode succeeding also proves input fidelity.

## 6. Negative controls (≥1; must reject as designed)
- Wrong keys: assert no valid answer format; near-miss garbage appears only at key-cycle positions.
- Payload-free carrier: both implementations return no message (empty/near-empty) — never fabricate.
- Single-char tamper: decode stays rc=0 but the message corrupts — proves bit-dependency AND that format self-checking is mandatory.
- Save every control's raw output.

## 7. Boundaries & verdict
- Classify each condition change as PASS (method holds) vs BOUNDARY (silent-fail mode, tool limit). A boundary found on an extra probe is a finding; keep it out of the counted pass-set.
- `Transfer-Validated` ONLY when the original reproduction AND all counted variants pass, with negative controls rejecting as designed. Otherwise name the exact failing item and stop short of the label.

## 8. Deliverables
Two reports (route comparison incl. detours; transfer verification incl. repro + variants + controls + boundary table + verdict), plus build/solve scripts, per-run logs, variant artifacts (carriers, encoded files, meta.json with sha256), and the cross-implementation call log (tool execution ids).
