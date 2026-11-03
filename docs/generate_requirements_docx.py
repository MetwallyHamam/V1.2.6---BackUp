from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "Documentation.md"
OUTPUT = ROOT / "MILLENSYS_Support_Hub_Documentation_Requirements.docx"


def shade(cell, fill: str) -> None:
    props = cell._tc.get_or_add_tcPr()
    element = OxmlElement("w:shd")
    element.set(qn("w:fill"), fill)
    props.append(element)


def set_cell_margins(cell, top=80, start=100, bottom=80, end=100) -> None:
    props = cell._tc.get_or_add_tcPr()
    margins = props.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        props.append(margins)
    for name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def add_field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "Right-click and update field"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instr, separate, text, end):
        run._r.append(node)


def add_inline(paragraph, text: str) -> None:
    # Render Markdown bold and inline-code spans while retaining all source text.
    pattern = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*)")
    cursor = 0
    for match in pattern.finditer(text):
        if match.start() > cursor:
            paragraph.add_run(text[cursor : match.start()])
        token = match.group(0)
        if token.startswith("**"):
            paragraph.add_run(token[2:-2]).bold = True
        else:
            run = paragraph.add_run(token[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(31, 78, 121)
        cursor = match.end()
    if cursor < len(text):
        paragraph.add_run(text[cursor:])


def parse_table(lines: list[str], index: int):
    if index + 1 >= len(lines) or "|" not in lines[index + 1]:
        return None
    divider = lines[index + 1].strip().strip("|")
    if not all(re.fullmatch(r"\s*:?-{3,}:?\s*", c) for c in divider.split("|")):
        return None
    rows = []
    cursor = index
    while cursor < len(lines) and "|" in lines[cursor] and lines[cursor].strip():
        if cursor != index + 1:
            rows.append([c.strip() for c in lines[cursor].strip().strip("|").split("|")])
        cursor += 1
    return rows, cursor


def configure(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.08

    colors = ["17365D", "1F4E79", "2F75B5", "5B9BD5", "70AD47", "7F6000"]
    sizes = [18, 15, 12, 11, 10, 10]
    for level in range(1, 7):
        style = doc.styles[f"Heading {level}"]
        style.font.name = "Aptos Display"
        style.font.size = Pt(sizes[level - 1])
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(colors[level - 1])
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = Pt(12 if level <= 2 else 8)
        style.paragraph_format.space_after = Pt(5)

    code = doc.styles.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
    code.font.name = "Consolas"
    code.font.size = Pt(8.5)
    code.font.color.rgb = RGBColor(45, 45, 45)
    code.paragraph_format.left_indent = Inches(0.25)
    code.paragraph_format.right_indent = Inches(0.1)
    code.paragraph_format.space_before = Pt(3)
    code.paragraph_format.space_after = Pt(3)


def add_title_page(doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(125)
    r = p.add_run("MILLENSYS")
    r.bold = True
    r.font.name = "Aptos Display"
    r.font.size = Pt(28)
    r.font.color.rgb = RGBColor(23, 54, 93)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Support Hub System Documentation")
    r.bold = True
    r.font.name = "Aptos Display"
    r.font.size = Pt(23)
    r.font.color.rgb = RGBColor(31, 78, 121)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Requirements Specification")
    r.font.size = Pt(16)
    r.font.color.rgb = RGBColor(89, 89, 89)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(40)
    p.add_run(f"Generated from docs/Documentation.md\n{date.today().isoformat()}")
    p.runs[0].font.size = Pt(10)
    p.runs[0].font.color.rgb = RGBColor(100, 100, 100)
    doc.add_page_break()

    doc.add_heading("Table of Contents", level=1)
    toc = doc.add_paragraph()
    add_field(toc, 'TOC \\o "1-3" \\h \\z \\u')
    doc.add_page_break()


def add_headers_footers(doc: Document) -> None:
    for section in doc.sections:
        header = section.header.paragraphs[0]
        header.text = "MILLENSYS Support Hub | Documentation Requirements"
        header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        header.runs[0].font.size = Pt(8)
        header.runs[0].font.color.rgb = RGBColor(110, 110, 110)
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.add_run("Page ")
        add_field(footer, "PAGE")


def convert() -> None:
    doc = Document()
    configure(doc)
    add_title_page(doc)
    lines = SOURCE.read_text(encoding="utf-8-sig").splitlines()
    index = 0
    in_code = False
    code_lines: list[str] = []

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                p = doc.add_paragraph(style="Code Block")
                p.paragraph_format.keep_together = True
                p.add_run("\n".join(code_lines))
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        if not stripped:
            index += 1
            continue

        table_data = parse_table(lines, index)
        if table_data:
            rows, index = table_data
            width = max(len(row) for row in rows)
            table = doc.add_table(rows=len(rows), cols=width)
            table.style = "Table Grid"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = True
            for r_idx, row in enumerate(rows):
                for c_idx in range(width):
                    cell = table.cell(r_idx, c_idx)
                    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    set_cell_margins(cell)
                    cell.text = ""
                    add_inline(cell.paragraphs[0], row[c_idx] if c_idx < len(row) else "")
                    for run in cell.paragraphs[0].runs:
                        run.font.size = Pt(8)
                        if r_idx == 0:
                            run.bold = True
                            run.font.color.rgb = RGBColor(255, 255, 255)
                    if r_idx == 0:
                        shade(cell, "1F4E79")
                    elif r_idx % 2 == 0:
                        shade(cell, "EAF2F8")
            doc.add_paragraph().paragraph_format.space_after = Pt(1)
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            # The source title is already represented by the cover page.
            if index != 0:
                doc.add_heading(title, level=level)
            index += 1
            continue

        bullet = re.match(r"^(\s*)[*+-]\s+(.*)$", line)
        numbered = re.match(r"^(\s*)\d+[.)]\s+(.*)$", line)
        checkbox = re.match(r"^(\s*)\[([ xX])\]\s+(.*)$", line)
        if checkbox:
            depth = min(len(checkbox.group(1)) // 2, 2)
            p = doc.add_paragraph(style="List Bullet" if depth == 0 else f"List Bullet {depth + 1}")
            add_inline(p, ("☒ " if checkbox.group(2).lower() == "x" else "☐ ") + checkbox.group(3))
        elif bullet:
            depth = min(len(bullet.group(1)) // 2, 2)
            p = doc.add_paragraph(style="List Bullet" if depth == 0 else f"List Bullet {depth + 1}")
            add_inline(p, bullet.group(2))
        elif numbered:
            depth = min(len(numbered.group(1)) // 2, 2)
            p = doc.add_paragraph(style="List Number" if depth == 0 else f"List Number {depth + 1}")
            add_inline(p, numbered.group(2))
        else:
            p = doc.add_paragraph()
            add_inline(p, stripped)
        index += 1

    add_headers_footers(doc)
    settings = doc.settings._element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)
    doc.core_properties.title = "MILLENSYS Support Hub System Documentation Requirements"
    doc.core_properties.subject = "Requirements for the complete documentation and handover package"
    doc.core_properties.author = "MILLENSYS"
    doc.core_properties.keywords = "Support Hub, requirements, documentation, handover"
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    convert()
