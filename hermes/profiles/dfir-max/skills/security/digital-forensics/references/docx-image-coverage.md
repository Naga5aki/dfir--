# Embedded Image OCR / Vision Fallback for DOCX Extraction

Reference for the `digital-forensics` skill, extending
`references/docx-content-extraction.md`. Read this when the DOCX has a
non-trivial `word/media/` payload and you need to decide how to cover
image content honestly.

## Why this needs its own note

A blog-export DOCX can easily carry 200+ PNGs in `word/media/`. Text
extraction (paragraphs, tables, text boxes) does NOT cover the pixels.
Saying "text coverage 100%" while silently skipping the images
misstates the audit; saying "coverage 0%" because you have no OCR
overstates the gap. This reference is the middle path: explicit,
per-image accounting with a concrete tool-resolution plan.

## Step 1 — Triage by size before deciding

Extract every `word/media/*` entry to a work directory. Record name,
byte size, and SHA-256 per file. Bucket by size:

| Bucket | Typical content | Action |
|---|---|---|
| `<200 B` | Placeholder spacer / 1-pixel transparent | Skip; count |
| `200 B – 1 KB` | Tiny icon, badge, divider | Skip unless referenced by a heading |
| `1 KB – 10 KB` | Small inline image, simple diagram | Sample-check a few |
| `10 KB – 50 KB` | Real screenshot or code image | OCR or vision |
| `50 KB – 200 KB` | Full screenshot | OCR or vision |
| `>200 KB` | High-res screenshot / scan | OCR or vision |

A real blog-export DOCX observed in the wild: 295 media files, of
which 140 were `<200 B` placeholders, 51 were `200 B – 1 KB` icons, and
only **90 were ≥10 KB** and actually carried content. The size filter
alone reduced the OCR workload by 70%.

Record the threshold you chose and the per-bucket counts in the
coverage manifest.

## Step 2 — Pick an OCR/vision backend

Preference order:

1. **Local OCR (`tesseract` via `pytesseract`)** — best for bulk text
   extraction, works offline, deterministic. Caveats: mixed
   Chinese/English accuracy with default `eng` model is poor; install
   `chi_sim` (or `chi_sim+eng`) explicitly and flag the model used.
2. **Agent `vision_analyze` tool** — best for screenshots whose
   content is UI, diagrams, or handwriting; handles mixed-language
   text well. Requires a configured vision backend (see Step 3).
3. **Manual review** — acceptable for a small number (<20) of images
   when the user is present. State it in the report.

Do NOT mark an image as covered merely because it was extracted to
disk. Extraction is inventory, not identification.

## Step 3 — When `vision_analyze` returns "No LLM provider configured for task=vision"

This means none of the vision-capable providers are reachable with
credentials. The resolution chain is, in order:

1. Active main provider, **if** it is a known vision backend
2. `openrouter` (needs `OPENROUTER_API_KEY`)
3. `nous` (needs Nous Portal OAuth via `hermes auth add nous`)
4. `deepinfra` (needs `DEEPINFRA_API_KEY`)
5. Custom endpoint via `auxiliary.vision.*` config

Cheapest fix: set `OPENROUTER_API_KEY`. Free vision SKUs exist (e.g.
`qwen/qwen2.5-vl-32b-instruct:free`,
`meta-llama/llama-3.2-11b-vision-instruct:free`); the
`auxiliary.free_only: true` config gate restricts the fallback to
those if you want cost certainty.

Alternative: point vision at a local model server (Ollama with
`llava`, `qwen2.5-vl`, etc.) via:

```yaml
auxiliary:
  vision:
    provider: custom
    base_url: "http://localhost:11434/v1"
    model: "qwen2.5-vl:7b"
```

Do not tell the user "vision is unavailable" without naming which key
or config section would enable it. The remediation is the useful part
of the error message.

## Step 4 — Per-image coverage accounting

Every embedded image gets exactly one status in the coverage manifest:

| Status | Meaning |
|---|---|
| `ocr_ok` | Text extracted via OCR; confidence noted |
| `vision_ok` | Analyzed by `vision_analyze`; summary stored |
| `skipped_size` | Below the chosen threshold; counted |
| `skipped_no_backend` | Needed vision but no backend configured |
| `manual_review` | User reviewed the image directly |

The manifest lists counts per status, not a single rolled-up
percentage. A "coverage 100%" claim is only defensible when every
image is in `ocr_ok`, `vision_ok`, or `manual_review`.

## Step 5 — Reintegrate findings

For images that carried text or code:

- append the extracted content to `extracted-content.md` under the
  image's source locator (`DOC-SECTION-...-E<n>`);
- tag it as `[OCR]` or `[VISION]` with the backend used;
- update the knowledge cards that referenced the image with the new
  source-derived text, keeping the original locator so a reviewer can
  trace back to the image itself.

For images that turned out to be decorative or already-known icons,
mark `skipped_size` (or equivalent) in the manifest and move on — do
not churn cards with "this was a spacer."

## Pitfalls

- **Alt text is almost always empty** in blog exports. Do not rely on
  `wp:docPr descr` to identify images.
- **The same image rId can be referenced from many paragraphs.** The
  manifest tracks unique image targets; the extraction records each
  reference. Don't double-count.
- **Image size ≠ importance.** A 300-byte PNG of an arrow is noise; a
  300-byte PNG containing a single Chinese character can be signal.
  Use the bucket as a prior, not a verdict, and sample-check at least
  one image from each bucket before writing the whole bucket off.
- **`wp:docPr name` is unreliable.** Names like `IM 42`, `Rect 7`,
  `Picture 3` are auto-generated and carry no semantic content.
