# DOCX Content Extraction for Forensic / Audit Reading

Reference for the `digital-forensics` skill. Read this when the evidence
file is a `.docx` and you need to inventory, audit, or fully extract its
content — especially files from untrusted sources, web/blog exports
(Hugo, WordPress, Confluence dumps), or environments where `python-docx`
is not installed.

This complements the bundled `docx` skill, which targets create / edit /
template workflows. This reference is about **read-only, complete,
verifiable extraction**.

## Read-only handling of the source `.docx`

Follow the umbrella's integrity rules, applied to a DOCX:

1. SHA-256 the source BEFORE opening it. Record the value.
2. Copy to a work directory; operate only on the copy. SHA-256 the copy
   and confirm equality.
3. After analysis, recompute source SHA-256 and confirm unchanged.
4. Remember: on NTFS, even read-only access can update `AccessTime`.
   Content hash equality does not prove metadata was untouched. For
   strict evidence preservation, work from a snapshot or no-atime mount
   and disclose the side effect.

## Reading without python-docx

A `.docx` is a ZIP. Python's standard library is sufficient:

```python
import zipfile
from xml.etree import ElementTree as ET

z = zipfile.ZipFile("file.docx")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

doc  = z.read("word/document.xml").decode("utf-8")
root = ET.fromstring(doc)
body = root.find(W + "body")
```

For untrusted files, `defusedxml` is preferred — OOXML XML can in
principle carry DTD/entity attacks. If you stay with stdlib, state the
choice and confirm the parts you parse have no `DOCTYPE` declaration.

### Namespaces you will actually need

| Alias | URI |
|---|---|
| `W` | `http://schemas.openxmlformats.org/wordprocessingml/2006/main` |
| `R` | `http://schemas.openxmlformats.org/officeDocument/2006/relationships` |
| `A` | `http://schemas.openxmlformats.org/drawingml/2006/main` |
| `WP` | `http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing` |
| `PIC` | `http://schemas.openxmlformats.org/drawingml/2006/picture` |
| `M` | `http://schemas.openxmlformats.org/officeDocument/2006/math` |

## Package inventory checklist

Bucket `z.namelist()` by prefix. The counts themselves are signal.

- `word/document.xml` — main story. Size is a complexity hint (a 10 MB
  `document.xml` is a heavy document even if paragraph count is small).
- `word/header*.xml` / `word/footer*.xml` — can legitimately number in
  the dozens or hundreds. Not corruption; one per section variant.
- `word/media/` — embedded images. Count, note size distribution, and
  cross-check which `rId`s are actually referenced from the body.
- `word/embeddings/` — OLE objects. Flag immediately.
- `word/charts/` — chart parts.
- `word/comments.xml` — presence means the doc has comments.
- `word/footnotes.xml` / `word/endnotes.xml` — almost always present
  with two empty placeholders (IDs 0 and 1, the separator/continuation
  entries). Real notes start at ID 2; zero real notes is normal.
- `word/vbaProject.bin` — macros. Stop and flag.
- `customXml/` — custom XML data parts. Usually ignorable for content
  extraction; say so explicitly if you skip them.
- `[Content_Types].xml`, `_rels/.rels`, `word/_rels/document.xml.rels` —
  the rId-to-target map. Needed to resolve images and hyperlinks.

## Detecting tracked changes, comments, and other live content

Scan the parsed body root:

```python
len(root.findall(".//" + W + "ins"))                # insertions
len(root.findall(".//" + W + "del"))                # deletions
len(root.findall(".//" + W + "moveFrom"))           # moves
len(root.findall(".//" + W + "moveTo"))
len(root.findall(".//" + W + "commentRangeStart"))  # comment anchors
len(root.findall(".//" + W + "OLEObject"))          # OLE
len(root.findall(".//" + M  + "oMath"))             # equations
```

Zero on all of the above is a real finding (no revisions, no comments,
no OLE, no math) — say it explicitly. Non-zero is also a finding: count
them, and if you cannot resolve their content, list them as a coverage
gap rather than silently omitting them.

## Text boxes are real content

Web-exported documents routinely put code blocks, callout boxes, and
admonitions inside `w:txbxContent`. Plain paragraph iteration will MISS
this text. Iterate text boxes explicitly:

```python
for tb in paragraph.iter(W + "txbxContent"):
    text = "".join(t.text or "" for t in tb.iter(W + "t"))
```

In one real blog export, 227 text boxes carried essentially all the
code samples. Skipping them silently dropped the document's most
valuable content — and the extract looked plausible at a glance.

## Style IDs do not equal style names

Do not trust `w:pStyle` IDs to mean what they look like. In one blog
export, styleId `2` had the *name* "Body Text" and was used as the
visual body style, while actual headings were marked by **font size and
bold**, not by any heading style. Always resolve via `word/styles.xml`:

```python
styles_root = ET.fromstring(z.read("word/styles.xml").decode("utf-8"))
style_map = {s.get(W + "styleId"): (s.find(W + "name").get(W + "val")
                                    if s.find(W + "name") is not None else None)
             for s in styles_root.findall(W + "style")}
```

## Inferring headings from run formatting

When no heading styles are used, infer headings from `w:rPr/w:sz` (size
in half-points) and `w:rPr/w:b` (bold), optionally plus
`w:pPr/w:outlineLvl`:

```python
def para_format(p):
    sizes, bolds = [], 0
    for r in p.iter(W + "r"):
        rPr = r.find(W + "rPr")
        if rPr is None: continue
        if rPr.find(W + "b") is not None:
            bolds += 1
        sz = rPr.find(W + "sz")
        if sz is not None and (sz.get(W + "val") or "").isdigit():
            sizes.append(int(sz.get(W + "val")))
    return (max(sizes) if sizes else 0, bolds > 0)
```

A heuristic like `max_size >= 31` (15.5 pt) AND `bold` is a reasonable
H2 threshold for many blog exports — but **calibrate on a sample of
known headings in the specific document** before applying globally.

## app.xml metadata is unreliable

`docProps/app.xml` carries `<Pages>`, `<Words>`, `<Characters>`, but
exporters often do not update them. In one real case it reported
`Pages=150, Words=740, Characters=1489` while actual extracted text was
over 75,000 characters — roughly a 50× underestimate. **Always extract
and count yourself**; treat app.xml as a hint at best, and flag large
discrepancies as a metadata-integrity observation, not a fact about the
document.

## Hyperlinks may not be `w:hyperlink`

Web exports often paste URLs as plain text rather than `w:hyperlink`
elements. A zero `w:hyperlink` count does NOT mean no URLs. Run a regex
over the extracted text (`https?://\S+`) to enumerate them separately,
and mark them as "text-only URLs, not clicked".

## Coverage accounting

For full-coverage audits, count and report each class separately:

- Top-level paragraphs (`w:p` direct children of `w:body`)
- Tables (`w:tbl`) with row/column dimensions
- Empty vs non-empty paragraphs (blog exports can have >1000 empty
  paragraphs used as spacers; report them as excluded-with-reason)
- Image references (`a:blip` rIds) vs unique image targets
- Text boxes (as above)
- Headers / footers / footnotes / endnotes, even when empty

Distinguish **text extracted** from **image content identified**. An
image whose pixels you have not OCR'd or viewed is a known coverage
gap. Say so in the report rather than claiming "full coverage".

## Pitfalls

- **Element counts lie by omission.** Iterating only `w:body` direct
  children misses nested tables, text-box paragraphs, and SDT content.
- **`sectPr` count is not page count.** One section can span 150 pages.
- **`w:br type="page"` count is not page count either.** Word paginates
  without explicit break runs.
- **Empty `footnote`/`endnote` IDs 0 and 1 are normal.** They are the
  separator/continuation entries, not real notes.
- **`wp:docPr descr=""` is usually empty.** Image alt text is almost
  always blank in exports; do not rely on it to identify image content.
- **A file opening in Word is not proof of structural validity.** It
  is corroboration at most; checksums, offsets, and references still
  need to be checked independently.

## Output shape for an extraction report

A reasonable layout for a forensic extraction:

```
work/<slug>/
  source-copy.docx          # working copy; SHA-256 matches source
  extracted-content.md      # every non-empty element, with locators
  coverage-manifest.md      # what was and was not covered
```

Use source locators that let a reviewer jump back to the source, e.g.
`DOC-SECTION-<heading-path>-E<seq>` when page numbers are unavailable
(no renderer), or `DOC-P<page>-S<section>-E<seq>` when they are. Never
fabricate page numbers.
