#!/usr/bin/env python3
"""Turn an agreed NDA Handshake result into a signable Word document.

Reads the result.json written by match.py and produces a .docx holding:
  1. the Common Paper Mutual NDA Cover Page, filled in with the agreed terms
  2. the Standard Terms, attached for convenience
  3. a one-page handshake record (not part of the agreement)

Only an AGREED result can be turned into a document. Nothing here signs
anything; the humans named on the Cover Page sign it.

Requires python-docx (pip install python-docx).
"""
import argparse
import json
import os
import re
import sys

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from match import change_list

HERE = os.path.dirname(os.path.abspath(__file__))
FORMS = {
    "common-paper-mnda-1.0": {
        "terms_file": os.path.join(HERE, "forms", "common-paper-mnda-1.0", "standard-terms.md"),
        "terms_url": "commonpaper.com/standards/mutual-nda/1.0",
        "attribution": ("Common Paper Mutual Non-Disclosure Agreement (Version 1.0) "
                        "free to use under CC BY 4.0."),
    }
}
STARTS = {"effective-date": "Effective Date", "last-disclosure": "the date of last disclosure"}


SERIF = "Georgia"
RULE = "B4B4B4"   # light grey rule between rows
SHADE = "F3F1EC"  # label column background


def add_runs(paragraph, text, size=None):
    """Add text to a paragraph, turning **bold** markers into bold runs."""
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if part:
            run = paragraph.add_run(part)
            run.bold = (i % 2 == 1)
            if size:
                run.font.size = Pt(size)


def _el(tag, **attrs):
    el = OxmlElement(tag)
    for key, value in attrs.items():
        el.set(qn(key), value)
    return el


def style_table(table, widths, rules=True, pad=70):
    """Fixed column widths, no outer box, optional thin rules between rows."""
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    tbl_pr.append(_el("w:tblW", **{"w:w": str(int(sum(widths) * 1440)), "w:type": "dxa"}))
    tbl_pr.append(_el("w:tblLayout", **{"w:type": "fixed"}))
    for column, width in zip(table.columns, widths):
        column.width = Inches(width)
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = Inches(width)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
            tc_pr = cell._tc.get_or_add_tcPr()
            borders = _el("w:tcBorders")
            for edge in ("top", "bottom"):
                if rules:
                    borders.append(_el(f"w:{edge}", **{"w:val": "single", "w:sz": "4",
                                                      "w:space": "0", "w:color": RULE}))
                else:
                    borders.append(_el(f"w:{edge}", **{"w:val": "nil"}))
            for edge in ("left", "right"):
                borders.append(_el(f"w:{edge}", **{"w:val": "nil"}))
            tc_pr.append(borders)
            margins = _el("w:tcMar")
            for edge, twips in (("top", str(pad)), ("bottom", str(pad)), ("left", "140"), ("right", "140")):
                margins.append(_el(f"w:{edge}", **{"w:w": twips, "w:type": "dxa"}))
            tc_pr.append(margins)


def shade(cell):
    cell._tc.get_or_add_tcPr().append(
        _el("w:shd", **{"w:val": "clear", "w:color": "auto", "w:fill": SHADE}))


def tight(paragraph, after=0, before=0):
    paragraph.paragraph_format.space_after = Pt(after)
    paragraph.paragraph_format.space_before = Pt(before)
    return paragraph


def field_row(table, label, hint, lines):
    cells = table.add_row().cells
    shade(cells[0])
    tight(cells[0].paragraphs[0]).add_run(label).bold = True
    if hint:
        run = tight(cells[0].add_paragraph(), before=2).add_run(hint)
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    tight(cells[1].paragraphs[0]).add_run(lines[0])
    for line in lines[1:]:
        tight(cells[1].add_paragraph(), before=4).add_run(line)


def add_field(paragraph, instruction):
    """Insert a Word field such as PAGE or NUMPAGES."""
    field = _el("w:fldSimple", **{"w:instr": instruction})
    run = _el("w:r")
    props = _el("w:rPr")
    props.append(_el("w:sz", **{"w:val": "17"}))
    run.append(props)
    text = _el("w:t")
    text.text = "1"
    run.append(text)
    field.append(run)
    paragraph._p.append(field)


def title(doc, text, page_break=False):
    """A section title in Word's own Heading 1 style, so navigation and screen readers see it."""
    p = doc.add_paragraph(style="Heading 1")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.page_break_before = page_break
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(10)
    p.paragraph_format.keep_with_next = True
    p.add_run(text.upper())
    return p


def party_line(p):
    return f"a {p['formed_in']} {p['entity_type']}"


def signature_block(doc, parties):
    """Two signature blocks side by side, one table row per line so they stay aligned."""
    grey = RGBColor(0x55, 0x55, 0x55)
    rows = [
        ([f"PARTY {i}" for i in (1, 2)], dict(size=8.5, color=grey)),
        ([p["legal_name"].upper() for p in parties], dict(bold=True)),
        ([party_line(p) for p in parties], dict(size=9.5)),
        (["Signature:  " + "_" * 22] * 2, dict(before=12)),
        (["Print Name:  " + p["signatory_name"] for p in parties], {}),
        (["Title:  " + p["signatory_title"] for p in parties], {}),
        (["Notice Address:  " + p["notice_email"] for p in parties], {}),
        (["Date:  " + "_" * 20] * 2, {}),
    ]
    table = doc.add_table(rows=0, cols=2)
    for index, (texts, fmt) in enumerate(rows):
        row = table.add_row()
        row._tr.get_or_add_trPr().append(_el("w:cantSplit"))
        for cell, text in zip(row.cells, texts):
            para = tight(cell.paragraphs[0], before=fmt.get("before", 0))
            # Keep the whole block on one page.
            para.paragraph_format.keep_with_next = index < len(rows) - 1
            run = para.add_run(text)
            run.bold = fmt.get("bold", False)
            if "size" in fmt:
                run.font.size = Pt(fmt["size"])
            if "color" in fmt:
                run.font.color.rgb = fmt["color"]
    style_table(table, [3.15, 3.15], rules=False, pad=28)


TERM_LABELS = {
    "form": "Standard form",
    "nda_term_years": "NDA term",
    "confidentiality_years": "Confidentiality period",
    "confidentiality_starts": "Period starts from",
    "governing_law": "Governing law",
    "venue": "Venue",
    "marking_requirement": "Marking requirement",
    "residuals": "Residuals clause",
    "affiliate_sharing": "Affiliate sharing",
}
OUTCOME_LABELS = {
    "MATCHED": "Matched",
    "MIDPOINT": "Midpoint",
    "BEST_SHARED": "Best shared option",
    "TIE_BREAK": "Tie-break",
    "ONE_SIDED": "One side's preference",
    "REQUIRED": "Required by one side",
    "NOT_INCLUDED": "Not included",
    "FORM_DEFAULT": "Form default",
}
VALUE_LABELS = {
    "common-paper-mnda-1.0": "Common Paper Mutual NDA v1.0",
    "effective-date": "Effective Date",
    "last-disclosure": "date of last disclosure",
    "none": "no marking required",
    "written-marked": "written material marked",
    "written-marked-oral-confirmed": "written marked, oral confirmed",
}


def plain(text):
    """Swap protocol keywords in a position or explanation for plain English."""
    for key, label in sorted(VALUE_LABELS.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(rf"(?<![\w-]){re.escape(key)}(?![\w-])", label, text)
    return text


def result_text(entry):
    value = entry["result"]
    if isinstance(value, bool):
        return "Included" if value else "Not included"
    if entry["term"].endswith("_years"):
        return f"{value} year(s)"
    text = plain(str(value))
    return text[0].upper() + text[1:]


def summary_table(doc, summary):
    """How each term was reached: both positions, the result and the rule applied."""
    table = doc.add_table(rows=1, cols=5)
    header = ["Term", summary["party_a"], summary["party_b"], "Result", "How it was reached"]
    for cell, text in zip(table.rows[0].cells, header):
        shade(cell)
        run = tight(cell.paragraphs[0]).add_run(text)
        run.bold = True
        run.font.size = Pt(8)
    for entry in summary["terms"]:
        cells = table.add_row().cells
        positions = [plain(entry[side]) for side in ("a", "b")]
        positions = [text[0].upper() + text[1:] for text in positions]
        texts = [TERM_LABELS.get(entry["term"], entry["term"]), *positions,
                 result_text(entry), None]
        for cell, text in zip(cells[:4], texts[:4]):
            tight(cell.paragraphs[0]).add_run(text).font.size = Pt(8)
        cells[0].paragraphs[0].runs[0].bold = True
        cells[3].paragraphs[0].runs[0].bold = True
        para = tight(cells[4].paragraphs[0])
        label = para.add_run(OUTCOME_LABELS.get(entry["outcome"], entry["outcome"]) + ". ")
        label.bold = True
        label.font.size = Pt(8)
        para.add_run(plain(entry["how"]) + ".").font.size = Pt(8)
    style_table(table, [1.3, 1.15, 1.15, 1.0, 1.7], pad=50)


def build(result, draft_by=None):
    """Build the MNDA document.

    draft_by: the legal name of a company proposing these terms as an
    ordinary draft, with no handshake behind them. The document then has no
    handshake record or terms hash, and ends with a short note saying what
    it is.
    """
    terms = result["terms"]
    form = FORMS.get(terms["form"])
    if form is None:
        sys.exit(f"No cover page layout for form '{terms['form']}'")

    doc = Document()
    # Document properties tie this file to its data, so software that receives only
    # the document can find and verify the matching result.json.
    props = doc.core_properties
    props.title = "Mutual Non-Disclosure Agreement"
    props.subject = f"NDA Handshake protocol {terms['protocol_version']}; form {terms['form']}"
    if draft_by:
        props.keywords = "nda-handshake; ordinary-draft"
        props.comments = (f"Unsigned draft proposed by {draft_by}. "
                          "Not the result of a handshake.")
    else:
        props.keywords = f"nda-handshake; terms-hash:{result['terms_hash']}"
        props.comments = ("Unsigned draft produced by the NDA Handshake matcher. "
                          f"Terms hash (SHA-256): {result['terms_hash']}")
    props.author = "NDA Handshake"
    normal = doc.styles["Normal"]
    normal.font.name = SERIF
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), SERIF)
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.1
    heading = doc.styles["Heading 1"]
    heading.font.name = SERIF
    heading.font.size = Pt(15)
    heading.font.bold = True
    heading.font.color.rgb = RGBColor(0, 0, 0)
    fonts = heading.element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attr), SERIF)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if fonts.get(qn(attr)) is not None:
            del fonts.attrib[qn(attr)]
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Inches(0.85)
    section.left_margin = section.right_margin = Inches(1.1)

    # Footer on every page: the form's attribution line and a page number.
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.paragraph_format.space_after = Pt(2)
    footer.add_run(form["attribution"]).font.size = Pt(8)
    pages = section.footer.add_paragraph()
    pages.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pages.add_run("Page ").font.size = Pt(8.5)
    add_field(pages, "PAGE")
    pages.add_run(" of ").font.size = Pt(8.5)
    add_field(pages, "NUMPAGES")

    # 1. Cover Page
    title(doc, "Mutual Non-Disclosure Agreement")
    intro = doc.add_paragraph()
    intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    intro.paragraph_format.space_after = Pt(10)
    add_runs(intro, (
        "This Mutual Non-Disclosure Agreement (the “**MNDA**”) consists of: (1) this "
        "Cover Page (“**Cover Page**”) and (2) the Common Paper Mutual NDA Standard "
        f"Terms Version 1.0 posted at {form['terms_url']} (“**Standard Terms**”). A "
        "copy of the Standard Terms is attached for convenience only. Any modifications "
        "of the Standard Terms should be made on the Cover Page, which will control over "
        "conflicts with the Standard Terms."))

    table = doc.add_table(rows=0, cols=2)
    changes = change_list(terms)
    law = terms["governing_law"]
    law_text = ("The laws of the District of Columbia." if law == "District of Columbia"
                else f"The laws of the State of {law}.")
    field_row(table, "Purpose", "How Confidential Information may be used", [terms["purpose"]])
    field_row(table, "Effective Date", None, ["Date of last Cover Page signature"])
    field_row(table, "MNDA Term", "Period for sharing Confidential Information", [
        f"☒  Expires {terms['nda_term_years']} year(s) from Effective Date.",
        "☐  Continues until terminated in accordance with the terms of the MNDA."])
    field_row(table, "Term of Confidentiality", "How long Confidential Information is protected", [
        f"☒  {terms['confidentiality_years']} year(s) from "
        f"{STARTS[terms['confidentiality_starts']]}, but in the case of trade secrets, until "
        "Confidential Information is no longer considered a trade secret under applicable laws.",
        "☐  In perpetuity."])
    field_row(table, "Governing Law", None, [law_text])
    field_row(table, "Jurisdiction", None,
              [f"The state and federal courts located in {terms['venue']}."])
    field_row(table, "Changes to Standard Terms",
              "List specific changes to the Standard Terms", changes or ["None."])
    style_table(table, [2.0, 4.3])

    closing = doc.add_paragraph()
    closing.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    closing.paragraph_format.space_before = Pt(12)
    closing.paragraph_format.keep_with_next = True
    closing.add_run(
        "Neither party has changed the Standard Terms, except for the details on the Cover "
        "Page above. By signing this Cover Page, each party agrees to enter into this MNDA "
        "as of the Effective Date.")

    signature_block(doc, terms["parties"])

    # 2. Standard Terms, attached for convenience
    title(doc, "Standard Terms", page_break=True)
    text = open(form["terms_file"], encoding="utf-8").read()
    text = re.sub(r"</?span[^>]*>", "", text)
    for line in text.splitlines():
        line = line.strip()
        # Skip headings and the attribution line, which is already in the footer.
        if not line or line.startswith("#") or line.startswith("Common Paper Mutual"):
            continue
        number, body = re.match(r"(\d+\.)\s+(.*)", line).groups()
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        para.paragraph_format.left_indent = Inches(0.35)
        para.paragraph_format.first_line_indent = Inches(-0.35)
        para.paragraph_format.tab_stops.add_tab_stop(Inches(0.35))
        para.paragraph_format.space_after = Pt(7)
        add_runs(para, number + "\t" + re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", body), size=9.5)

    if draft_by:
        # 3. A note on what this draft is, in place of a handshake record.
        title(doc, "About This Draft", page_break=True)
        for text in (
            f"This draft was prepared by {draft_by}. It is an ordinary draft for "
            "discussion and is not part of the MNDA.",
            "The agreement is the Common Paper Mutual NDA, a standard form that is free "
            "to use. The Standard Terms attached are unchanged. The only choices made "
            f"are the ones on the Cover Page, and they are {draft_by}'s preferred "
            "positions.",
            "Mark it up or comment on it as you would any draft. Fill in your company's "
            "details in the bracketed places in the signature block."):
            doc.add_paragraph(text).paragraph_format.space_after = Pt(8)
        return doc

    # 3. Handshake record
    title(doc, "NDA Handshake Record", page_break=True)
    note = doc.add_paragraph(
        "This page records how the terms on the Cover Page were reached. It is not part "
        "of the MNDA. It restates positions each party disclosed to the other in its "
        "nda-handshake.md file.")
    note.paragraph_format.space_after = Pt(10)

    summary = result.get("summary")
    if summary:
        counts = {}
        for entry in summary["terms"]:
            label = OUTCOME_LABELS.get(entry["outcome"], entry["outcome"]).lower()
            counts[label] = counts.get(label, 0) + 1
        tally = ", ".join(f"{n} {label}" for label, n in counts.items())
        line = doc.add_paragraph()
        line.paragraph_format.space_after = Pt(6)
        line.add_run(f"How the {len(summary['terms'])} terms were reached: ").bold = True
        line.add_run(tally + ".")
        summary_table(doc, summary)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    record = doc.add_table(rows=0, cols=2)
    rows = [("Protocol version", terms["protocol_version"]),
            ("Terms hash (SHA-256)", result["terms_hash"])]
    rows += [("Input file fingerprint (SHA-256)", fp)
             for fp in result.get("file_fingerprints", [])]
    for label, value in rows:
        cells = record.add_row().cells
        shade(cells[0])
        tight(cells[0].paragraphs[0]).add_run(label).bold = True
        run = tight(cells[1].paragraphs[0]).add_run(value)
        run.font.name = "Courier New"
        run.font.size = Pt(7.5)
    style_table(record, [2.0, 4.3])
    return doc


def main():
    ap = argparse.ArgumentParser(description="Make a signable Word cover page from result.json")
    ap.add_argument("result", help="Path to a result.json written by match.py")
    ap.add_argument("-o", "--out", help="Output .docx (default: next to result.json)")
    args = ap.parse_args()

    with open(args.result, encoding="utf-8") as f:
        result = json.load(f)
    if result.get("status") != "AGREED":
        sys.exit(f"Status is {result.get('status')}, not AGREED. A signable document is "
                 "only produced once every term is agreed and every party fact is present.")
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.result)), "mnda.docx")
    build(result).save(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
