from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


CN_DIGITS = "零一二三四五六七八九"


def cn_num(n: int) -> str:
    if n <= 0:
        return str(n)
    if n < 10:
        return CN_DIGITS[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + CN_DIGITS[n % 10]
    if n < 100:
        tens, ones = divmod(n, 10)
        return CN_DIGITS[tens] + "十" + (CN_DIGITS[ones] if ones else "")
    hundreds, rest = divmod(n, 100)
    if rest == 0:
        return CN_DIGITS[hundreds] + "百"
    if rest < 10:
        return CN_DIGITS[hundreds] + "百零" + CN_DIGITS[rest]
    return CN_DIGITS[hundreds] + "百" + cn_num(rest)


def set_run_font(
    run,
    east_asia: str = "仿宋",
    ascii_font: str = "Times New Roman",
    size: int = 16,
    bold: bool = False,
) -> None:
    run.font.name = ascii_font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), east_asia)
    run.font.size = Pt(size)
    run.bold = bold


def set_first_line_indent(paragraph, chars: int = 2) -> None:
    """Set first-line indent by Chinese character count, matching Word's character unit."""
    p_pr = paragraph._p.get_or_add_pPr()
    ind = p_pr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        p_pr.append(ind)

    for attr in ("firstLine", "hanging", "hangingChars"):
        q_attr = qn(f"w:{attr}")
        if q_attr in ind.attrib:
            del ind.attrib[q_attr]
    ind.set(qn("w:firstLineChars"), str(chars * 100))


def set_paragraph_format(
    paragraph,
    *,
    first_line: bool = True,
    align=None,
    line_pt: int = 28,
    before: int = 0,
    after: int = 0,
) -> None:
    fmt = paragraph.paragraph_format
    fmt.line_spacing = Pt(line_pt)
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    if first_line:
        set_first_line_indent(paragraph, chars=2)
    else:
        fmt.first_line_indent = Cm(0)
    if align is not None:
        paragraph.alignment = align


def set_cell_shading(cell, fill: str = "F2F2F2") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_margins(cell, top: int = 80, start: int = 80, bottom: int = 80, end: int = 80) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)

    for name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)

    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "6")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "808080")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = tr_pr.find(qn("w:tblHeader"))
    if tbl_header is None:
        tbl_header = OxmlElement("w:tblHeader")
        tr_pr.append(tbl_header)
    tbl_header.set(qn("w:val"), "true")


def set_row_cant_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = tr_pr.find(qn("w:cantSplit"))
    if cant_split is None:
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)
    cant_split.set(qn("w:val"), "true")


def clean_inline(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
    text = text.replace("`", "")
    return text.strip()


def normalize_heading_text(text: str) -> str:
    text = clean_inline(text)
    patterns = [
        r"^\d+(?:\.\d+)*\.?\s*",
        r"^[一二三四五六七八九十百]+[、.．]\s*",
        r"^（[一二三四五六七八九十百]+）\s*",
        r"^\([一二三四五六七八九十百]+\)\s*",
        r"^[（(]\d+[）)]\s*",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text)
    return text.strip()


def remove_front_matter(lines: list[str]) -> list[str]:
    if lines and lines[0].strip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                return lines[idx + 1 :]
    return lines


def is_table_separator(parts: list[str]) -> bool:
    return all(set(part.strip()) <= {"-", ":", " "} and part.strip() for part in parts)


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    table_lines = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        table_lines.append(lines[i].strip())
        i += 1

    rows = []
    for idx, line in enumerate(table_lines):
        parts = [clean_inline(part.strip()) for part in line.strip("|").split("|")]
        if idx == 1 and is_table_separator(parts):
            continue
        rows.append(parts)
    return rows, i


def add_main_title(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    set_paragraph_format(
        paragraph,
        first_line=False,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        line_pt=30,
        after=18,
    )
    run = paragraph.add_run(text)
    set_run_font(run, east_asia="方正小标宋简体", size=22)


def add_heading(doc: Document, text: str, level: int) -> None:
    paragraph = doc.add_paragraph()
    if level == 1:
        set_paragraph_format(paragraph, first_line=False, before=8, after=4)
        run = paragraph.add_run(text)
        set_run_font(run, east_asia="黑体", size=16)
    elif level == 2:
        set_paragraph_format(paragraph, first_line=True, before=4, after=2)
        run = paragraph.add_run(text)
        set_run_font(run, east_asia="楷体", size=16)
    else:
        set_paragraph_format(paragraph, first_line=True, before=2, after=0)
        run = paragraph.add_run(text)
        set_run_font(run, east_asia="仿宋", size=16)


def add_body_paragraph(doc: Document, text: str, *, quote: bool = False) -> None:
    if not text:
        return
    paragraph = doc.add_paragraph()
    if quote:
        set_paragraph_format(paragraph, first_line=False, before=3, after=3)
        paragraph.paragraph_format.left_indent = Cm(0.74)
        run = paragraph.add_run(clean_inline(text))
        set_run_font(run, east_asia="楷体", size=16)
    else:
        set_paragraph_format(paragraph, first_line=True)
        run = paragraph.add_run(clean_inline(text))
        set_run_font(run, size=16)


def add_list_paragraph(doc: Document, index: int, text: str) -> None:
    add_body_paragraph(doc, f"{index}. {clean_inline(text)}")


def add_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return

    cols = max(len(row) for row in rows)
    table = doc.add_table(rows=len(rows), cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    set_table_borders(table)
    set_repeat_table_header(table.rows[0])

    if cols >= 7:
        table_font_size = 10
    elif cols >= 5:
        table_font_size = 11
    else:
        table_font_size = None

    for r_idx, row in enumerate(rows):
        set_row_cant_split(table.rows[r_idx])
        for c_idx in range(cols):
            cell = table.cell(r_idx, c_idx)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            text = row[c_idx] if c_idx < len(row) else ""
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if r_idx == 0 else WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.line_spacing = Pt(22)
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(text)
            font_size = table_font_size or (12 if len(text) > 28 else 14)
            set_run_font(run, size=font_size, bold=(r_idx == 0))
            if r_idx == 0:
                set_cell_shading(cell)

    spacer = doc.add_paragraph()
    set_paragraph_format(spacer, first_line=False, line_pt=8)


def join_wrapped_text(parts: list[str]) -> str:
    text = ""
    for part in parts:
        part = part.strip()
        if not text:
            text = part
            continue
        if re.search(r"[A-Za-z0-9]$", text) and re.search(r"^[A-Za-z0-9]", part):
            text += " " + part
        else:
            text += part
    return text


def flush_paragraph(doc: Document, buffer: list[str]) -> None:
    if buffer:
        add_body_paragraph(doc, join_wrapped_text(buffer))
        buffer.clear()


def configure_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.start_type = WD_SECTION_START.NEW_PAGE
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(3.7)
    section.bottom_margin = Cm(3.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.6)

    styles = doc.styles
    styles["Normal"].font.name = "Times New Roman"
    styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "仿宋")
    styles["Normal"].font.size = Pt(16)
    return doc


def convert_markdown_to_docx(src: Path, out: Path, title: str | None = None) -> None:
    lines = remove_front_matter(src.read_text(encoding="utf-8").splitlines())
    doc = configure_document()

    counters = {1: 0, 2: 0, 3: 0, 4: 0}
    list_count = 0
    paragraph_buffer: list[str] = []
    in_code = False
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph(doc, paragraph_buffer)
            in_code = not in_code
            i += 1
            continue

        if in_code:
            if stripped:
                add_body_paragraph(doc, stripped, quote=True)
            i += 1
            continue

        if not stripped:
            flush_paragraph(doc, paragraph_buffer)
            list_count = 0
            i += 1
            continue

        if stripped in {"---", "***", "___"}:
            flush_paragraph(doc, paragraph_buffer)
            list_count = 0
            i += 1
            continue

        if stripped.startswith("|"):
            flush_paragraph(doc, paragraph_buffer)
            list_count = 0
            rows, i = parse_table(lines, i)
            add_table(doc, rows)
            continue

        heading_match = re.match(r"^(#{1,5})\s+(.+)$", stripped)
        if heading_match:
            flush_paragraph(doc, paragraph_buffer)
            list_count = 0
            level = len(heading_match.group(1))
            heading_text = normalize_heading_text(heading_match.group(2))

            if level == 1:
                add_main_title(doc, title or heading_text)
            elif level == 2:
                counters[1] += 1
                counters[2] = counters[3] = counters[4] = 0
                add_heading(doc, f"{cn_num(counters[1])}、{heading_text}", 1)
            elif level == 3:
                counters[2] += 1
                counters[3] = counters[4] = 0
                add_heading(doc, f"（{cn_num(counters[2])}）{heading_text}", 2)
            elif level == 4:
                counters[3] += 1
                counters[4] = 0
                add_heading(doc, f"{counters[3]}. {heading_text}", 3)
            else:
                counters[4] += 1
                add_heading(doc, f"（{counters[4]}）{heading_text}", 4)
            i += 1
            continue

        quote_match = re.match(r"^>\s*(.+)$", stripped)
        if quote_match:
            flush_paragraph(doc, paragraph_buffer)
            list_count = 0
            add_body_paragraph(doc, quote_match.group(1), quote=True)
            i += 1
            continue

        list_match = re.match(r"^\s*(?:[-*+]|\d+[.)]|[（(]\d+[）)])\s+(.+)$", line)
        if list_match:
            flush_paragraph(doc, paragraph_buffer)
            list_count += 1
            add_list_paragraph(doc, list_count, list_match.group(1))
            i += 1
            continue

        paragraph_buffer.append(stripped)
        i += 1

    flush_paragraph(doc, paragraph_buffer)

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Markdown to a Chinese public-document styled Word file.")
    parser.add_argument("input", type=Path, help="Markdown source file.")
    parser.add_argument("-o", "--output", type=Path, help="Output .docx path. Defaults to input basename.")
    parser.add_argument("--title", help="Override the # heading used as the main title.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    src = args.input
    if not src.exists():
        raise FileNotFoundError(src)
    out = args.output or src.with_suffix(".docx")
    convert_markdown_to_docx(src, out, args.title)
    print(out)


if __name__ == "__main__":
    main()
