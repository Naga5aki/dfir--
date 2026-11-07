# Leak-scan design (new content vs history)

Goal: prove newly promoted content carries zero source-specific fingerprints — without deleting or rewriting history.

## Patterns

Each pattern is a named entry; assert every alternative is non-empty (an empty alternative matches everything and voids the scan).

- flag-like tokens; hex hashes of 32/40/64 chars (word-bounded); IPv4; domains; email / phone / national-ID shapes; credential assignments; task/question-ID shapes; sample/case paths; controlled sizes and counts, both comma-grouped and plain forms; known page/index fingerprints; full ISO timestamps (one-time times).
- Encoded-form checks: base64 AND hex of the controlled values, searched as alternates (encoded leaks survive naive scans).
- Numeric-combo rule: flag any line containing ≥2 members of the controlled number set with at least one "strong" member — bare numbers are how fingerprints sneak through.
- Bounded number patterns also match substrings INSIDE hex digests (the flanking chars are letters, e.g. `90` in `…adf90b…`). Exclude full hex runs before number scanning, or classify such a hit by its container token — never count it as a number hit.
- **Digit boundaries for numeric-shaped tokens.** Match controlled numbers / ports / times with `(?<!\d)TOKEN(?!\d)`; plain substring matching false-fires whenever the token hides inside a longer constant (`536` inside `65536`) and per-hit hand explanations do not scale. String tokens (names, phrases, credentials) stay substring matches.
- Scope each pattern to what it protects: NAME patterns for "forbidden artifact exists" walks, TOKEN patterns for content scans. A required compliance phrase must not be able to trip the token pattern.

## Classification

- Build the pre-change line set from the backup; iterate the new files line by line; a hit whose line also exists in the backup is PRE-EXISTING, otherwise NEW.
- Hard gate: `new_hits_unexplained == 0`. "Explained" means matched to an explicit allowed class: tool-binary hash in a tool-fact line (tools are facts; sample hashes are not), policy statement that names the prohibited category, mandated registration text, already-characterized encoding collisions.
- **64-hex severity split, mechanically:** build a store of SHA-256s of every known file (case tree + formal stores + reports + backups) fresh each scan; a 64-hex hit that matches the store is a sample-hash leak (hard block); a hit matching nothing is an external fingerprint (tool binary, third-party artifact) — record-only weakness, since pinning tool identity hashes is established house style in tooling registries. Rebuilding the store per scan keeps it honest as artifacts grow.
- **Scan the pending write set before any store is touched:** emit all edit new-texts and new-file bodies into one staging scan-target and gate on it first; a post-write-only scan cannot prevent a bad write, only document it. Re-scan the live targets afterwards for the final verdict.
- Pre-existing hits: keep them, write one explanation each (prior-round registration; history is preserved by rule). Never delete to force a zero.
- Policy lines legitimately contain the forbidden vocabulary ("we do not record flags / question ids") — exempt them explicitly rather than weakening the pattern.
- Gate scope: the hard gate is the surface actually being written (the store, and any skill files changed this round); narrative deliverables (case report, appended records) get an informational pass where case titles and work paths classify as `record_context`, not leaks.
- A report or manifest that documents the store's own before/after hashes legitimately carries many 64-hex hits — that is the round's change ledger (consolidation class), not sample answers. Classify and count them; do not strip.
- A scan target that does not exist yet (report still pending) is skipped with a note, never an abort; re-run the scan after record appends so the verdict covers the final bytes.

## Artifact shape

`{generated, scope, patterns[], total_hits, new_hits, new_hits_allowed, new_hits_unexplained[], verdict, hits:[{file, line, pattern, match, class, explain}]}` — every hit carries a non-empty explanation; the validator later re-runs a live NEW-content variant for tamper detection.

## Reporting

State three numbers in the report: total hits, new hits, new unexplained (must be 0). List the pre-existing hits' explanations or point to the JSON that holds them. Say explicitly that history was preserved rather than cleaned.
