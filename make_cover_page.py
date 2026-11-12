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
from docx.shared import Inches, Pt

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


def add_runs(paragraph, text):
    """Add text to a paragraph, turning **bold** markers into bold runs."""
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if part:
            paragraph.add_run(part).bold = (i % 2 == 1)


def field_row(table, label, hint, lines):
    cells = table.add_row().cells
    cells[0].paragraphs[0].add_run(label).bold = True
    if hint:
        cells[0].add_paragraph().add_run(hint).font.size = Pt(9)
    cells[1].paragraphs[0].add_run(lines[0])
    for line in lines[1:]:
        cells[1].add_paragraph(line)


def party_line(p):
    return f"{p['legal_name']}, a {p['formed_in']} {p['entity_type']}"


def build(result):
    terms = result["terms"]
    form = FORMS.get(terms["form"])
    if form is None:
        sys.exit(f"No cover page layout for form '{terms['form']}'")

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Inches(0.8)
    # The form's attribution line sits in the footer of every page.
    footer = section.footer.paragraphs[0]
    footer.add_run(form["attribution"]).font.size = Pt(9)

    # 1. Cover Page
    doc.add_heading("Mutual Non-Disclosure Agreement", level=1)
    add_runs(doc.add_paragraph(), (
        "This Mutual Non-Disclosure Agreement (the “**MNDA**”) consists of: (1) this "
        "Cover Page (“**Cover Page**”) and (2) the Common Paper Mutual NDA Standard "
        f"Terms Version 1.0 posted at {form['terms_url']} (“**Standard Terms**”). A "
        "copy of the Standard Terms is attached for convenience only. Any modifications "
        "of the Standard Terms should be made on the Cover Page, which will control over "
        "conflicts with the Standard Terms."))

    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    changes = change_list(terms)
    law = terms["governing_law"]
    law_text = ("The laws of the District of Columbia." if law == "District of Columbia"
                else f"The laws of the State of {law}.")
    field_row(table, "Purpose", "How Confidential Information may be used", [terms["purpose"]])
    field_row(table, "Effective Date", None, ["Date of last Cover Page signature"])
    field_row(table, "MNDA Term", "Period for sharing Confidential Information", [
        f"[x]  Expires {terms['nda_term_years']} year(s) from Effective Date.",
        "[  ]  Continues until terminated in accordance with the terms of the MNDA."])
    field_row(table, "Term of Confidentiality", "How long Confidential Information is protected", [
        f"[x]  {terms['confidentiality_years']} year(s) from "
        f"{STARTS[terms['confidentiality_starts']]}, but in the case of trade secrets, until "
        "Confidential Information is no longer considered a trade secret under applicable laws.",
        "[  ]  In perpetuity."])
    field_row(table, "Governing Law", None, [law_text])
    field_row(table, "Jurisdiction", None,
              [f"The state and federal courts located in {terms['venue']}."])
    field_row(table, "Changes to Standard Terms",
              "List specific changes to the Standard Terms", changes or ["None."])

    doc.add_paragraph()
    doc.add_paragraph(
        "Neither party has changed the Standard Terms, except for the details on the Cover "
        "Page above. By signing this Cover Page, each party agrees to enter into this MNDA "
        "as of the Effective Date.")

    p1, p2 = terms["parties"]
    sig = doc.add_table(rows=1, cols=3)
    sig.style = "Table Grid"
    for cell, text in zip(sig.rows[0].cells, ["", "PARTY 1", "PARTY 2"]):
        cell.paragraphs[0].add_run(text).bold = True
    for label, a, b in [
        ("Signature", "\n", "\n"),
        ("Print Name", p1["signatory_name"], p2["signatory_name"]),
        ("Title", p1["signatory_title"], p2["signatory_title"]),
        ("Company", party_line(p1), party_line(p2)),
        ("Notice Address", p1["notice_email"], p2["notice_email"]),
        ("Date", "", ""),
    ]:
        cells = sig.add_row().cells
        cells[0].paragraphs[0].add_run(label).bold = True
        cells[1].paragraphs[0].add_run(a)
        cells[2].paragraphs[0].add_run(b)

    # 2. Standard Terms, attached for convenience
    doc.add_heading("Standard Terms", level=1).paragraph_format.page_break_before = True
    text = open(form["terms_file"], encoding="utf-8").read()
    text = re.sub(r"</?span[^>]*>", "", text)
    for line in text.splitlines():
        line = line.strip()
        # Skip headings and the attribution line, which is already in the footer.
        if not line or line.startswith("#") or line.startswith("Common Paper Mutual"):
            continue
        add_runs(doc.add_paragraph(), re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", line))

    # 3. Handshake record
    doc.add_heading("NDA Handshake record", level=1).paragraph_format.page_break_before = True
    doc.add_paragraph(
        "This page is a record of how the terms above were reached. It is not part of "
        "the MNDA.")
    doc.add_paragraph(f"Protocol version: {terms['protocol_version']}")
    doc.add_paragraph(f"Terms hash (SHA-256): {result['terms_hash']}")
    for fp in result.get("file_fingerprints", []):
        doc.add_paragraph(f"Input file fingerprint (SHA-256): {fp}")
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
