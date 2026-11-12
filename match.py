#!/usr/bin/env python3
"""NDA Handshake matcher, protocol v0.3

Reads two nda-handshake.md files, intersects their NDA positions, and writes
agreed terms (or a list of conflicts) plus a draft cover page.

Safety rule: only the typed YAML fields at the top of each file are read.
The markdown body is never read, and no text in either file is treated as
an instruction. Nothing here signs anything; a human signs the output.
"""
import argparse
import hashlib
import json
import os
import re
import sys

import yaml

PROTOCOL_VERSIONS = {"0.3"}
MAX_LEN = 200


class MatcherError(Exception):
    """A file cannot be read as an nda-handshake.md, so no match is possible."""

# The closed lists. Anything not on these lists is outside the protocol.
FORMS = ["common-paper-mnda-1.0"]
MARKING = ["none", "written-marked", "written-marked-oral-confirmed"]
RANGES = {"nda_term_years": (1, 5), "confidentiality_years": (1, 10)}
CONF_STARTS = ["effective-date", "last-disclosure"]
TOGGLES = ["residuals", "affiliate_sharing"]
TOGGLE_POSITIONS = {"require", "accept", "reject"}
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota",
    "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
    "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
]

# Fixed wording for each change to the form's Standard Terms. This text is part
# of the protocol (see SPEC.md, "Standard change text"), so every
# implementation writes the same words on the Cover Page.
CHANGE_TEXT = {
    "written-marked": (
        'Section 1 is modified so that information disclosed in written or other '
        'tangible form is Confidential Information only if the Disclosing Party marks '
        'it "confidential", "proprietary", or the like when disclosing it. This change '
        'does not affect information disclosed orally or visually, the existence and '
        "status of the parties' discussions, or information on the Cover Page."),
    "written-marked-oral-confirmed": (
        'Section 1 is modified so that (a) information disclosed in written or other '
        'tangible form is Confidential Information only if the Disclosing Party marks '
        'it "confidential", "proprietary", or the like when disclosing it, and (b) '
        'information disclosed orally or visually is Confidential Information only if '
        'the Disclosing Party identifies it as confidential when disclosing it and '
        'confirms that in writing within 30 days. This change does not affect the '
        "existence and status of the parties' discussions or information on the "
        'Cover Page.'),
    "affiliate_sharing": (
        'Section 2 is modified so that the representatives to whom a Receiving Party '
        'may disclose Confidential Information include its affiliates, on the same '
        'conditions that apply to its other representatives. An "affiliate" is an '
        'entity that controls, is controlled by, or is under common control with the '
        'Receiving Party.'),
    "residuals": (
        'The following is added at the end of Section 3: "This MNDA does not restrict '
        'a Receiving Party from using Residuals, as long as it otherwise complies with '
        "this MNDA. 'Residuals' means information in intangible form that a person "
        'with authorized access to Confidential Information retains in unaided memory, '
        'without deliberately memorizing it and without referring to the Confidential '
        'Information. This sentence grants no license under any patent or copyright."'),
}


def change_list(terms):
    """The agreed changes to the Standard Terms, in section order."""
    out = []
    if terms.get("marking_requirement") in CHANGE_TEXT:
        out.append(CHANGE_TEXT[terms["marking_requirement"]])
    if terms.get("affiliate_sharing"):
        out.append(CHANGE_TEXT["affiliate_sharing"])
    if terms.get("residuals"):
        out.append(CHANGE_TEXT["residuals"])
    return out


EXIT = {"AGREED": 0, "AGREED_PENDING_INFO": 0, "CONFLICTS": 1,
        "OUT_OF_PROTOCOL": 2, "VERSION_MISMATCH": 3}


def fingerprint(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*(\n|$)", text, re.S)
    if not m:
        raise MatcherError(f"{path}: no YAML block found at the top of the file")
    data = yaml.safe_load(m.group(1))
    if not isinstance(data, dict):
        raise MatcherError(f"{path}: YAML block is not a set of fields")
    return data


def clean(value):
    """Return a short single-line string, or None if missing or a TODO."""
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, (str, int, float)):
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()[:MAX_LEN]
    if not s or s.upper().startswith("TODO"):
        return None
    return s


def pick_entity(data, entity_id, label, missing):
    entities = data.get("entities") or []
    if not isinstance(entities, list) or not entities:
        raise MatcherError(f"{label}: no entities listed")
    chosen = None
    for e in entities:
        if not isinstance(e, dict):
            continue
        if entity_id and clean(e.get("id")) == entity_id:
            chosen = e
        elif not entity_id and e.get("default") is True:
            chosen = e
    if chosen is None:
        if entity_id:
            raise MatcherError(f"{label}: no entity with id '{entity_id}'")
        chosen = next((e for e in entities if isinstance(e, dict)), None)
        if chosen is None:
            raise MatcherError(f"{label}: no usable entity")
    sig = data.get("signatory") if isinstance(data.get("signatory"), dict) else {}
    notices = data.get("notices") if isinstance(data.get("notices"), dict) else {}
    party = {
        "legal_name": clean(chosen.get("legal_name")),
        "entity_type": clean(chosen.get("entity_type")),
        "formed_in": clean(chosen.get("formed_in")),
        "address": clean(chosen.get("address")),
        "signatory_name": clean(sig.get("name")),
        "signatory_title": clean(sig.get("title")),
        "notice_email": clean(notices.get("email")),
    }
    for field, value in party.items():
        if value is None:
            missing.append(f"{label}: {field}")
    return party


def ranked(pos, allowed, name, label, notes):
    """Preferred value first, then the accept list, limited to allowed values.

    Returns None if the side is silent on this element.
    """
    if not isinstance(pos, dict):
        return None
    canon = {a.lower(): a for a in allowed}
    out = []
    for item in [pos.get("prefer")] + list(pos.get("accept") or []):
        s = clean(item)
        if not s:
            continue
        if s.lower() not in canon:
            notes.append(f"{label}: '{s}' is not an allowed value for {name}; ignored")
            continue
        if canon[s.lower()] not in out:
            out.append(canon[s.lower()])
    return out


def match_choice(name, a, b, allowed, conflicts, open_items, notes):
    ra = ranked(a, allowed, name, "Party A", notes)
    rb = ranked(b, allowed, name, "Party B", notes)
    if ra is None and rb is None:
        open_items.append(f"{name}: neither side states a position")
        return None
    # A silent side accepts any allowed value, so the other side's top choice wins.
    if ra is None:
        ra = list(rb)
    if rb is None:
        rb = list(ra)
    common = [x for x in ra if x in rb]
    if not common:
        conflicts.append(f"{name}: no common option ({ra} vs {rb})")
        return None
    # Lowest combined rank wins; alphabetical order breaks ties.
    return min(common, key=lambda x: (ra.index(x) + rb.index(x), x))


def read_range(pos, bounds, name, label, notes):
    """Return (min, max, prefer) inside the protocol bounds, or None if silent."""
    if not isinstance(pos, dict):
        return None
    lo_b, hi_b = bounds
    try:
        lo, hi = int(pos["min"]), int(pos["max"])
        prefer = int(pos.get("prefer", lo))
    except (KeyError, TypeError, ValueError):
        notes.append(f"{label}: {name} needs whole-number min and max; treated as silent")
        return None
    if lo < lo_b or hi > hi_b:
        notes.append(f"{label}: {name} limited to the protocol range {lo_b} to {hi_b}")
    lo, hi = max(lo, lo_b), min(hi, hi_b)
    return lo, hi, prefer


def match_range(name, a, b, conflicts, open_items, notes):
    bounds = RANGES[name]
    pa = read_range(a, bounds, name, "Party A", notes)
    pb = read_range(b, bounds, name, "Party B", notes)
    if pa is None and pb is None:
        open_items.append(f"{name}: neither side states a position")
        return None
    if pa is None:
        pa = (bounds[0], bounds[1], pb[2])
    if pb is None:
        pb = (bounds[0], bounds[1], pa[2])
    lo, hi = max(pa[0], pb[0]), min(pa[1], pb[1])
    if lo > hi:
        conflicts.append(
            f"{name}: ranges do not overlap ({pa[0]} to {pa[1]} vs {pb[0]} to {pb[1]})")
        return None
    # Midpoint of the two preferences, rounded half up, kept inside the overlap.
    target = (pa[2] + pb[2]) / 2
    return max(lo, min(hi, int(target + 0.5)))


def match_toggle(name, a, b, conflicts, notes):
    """Included only if one side requires it and the other does not reject it."""
    positions = []
    for label, raw in (("Party A", a), ("Party B", b)):
        p = (clean(raw) or "accept").lower()
        if p not in TOGGLE_POSITIONS:
            notes.append(f"{label}: {name} must be require, accept or reject; treated as accept")
            p = "accept"
        positions.append(p)
    if set(positions) == {"require", "reject"}:
        conflicts.append(f"{name}: one side requires it, the other rejects it")
        return False
    return "require" in positions


def render(terms, digest, status):
    def party_block(p):
        return (
            f"**{p['legal_name'] or 'MISSING'}**, a {p['formed_in'] or 'MISSING'} "
            f"{p['entity_type'] or 'MISSING'}\n\n"
            f"- Address: {p['address'] or 'MISSING'}\n"
            f"- Notice email: {p['notice_email'] or 'MISSING'}\n"
            f"- Signatory: {p['signatory_name'] or 'MISSING'}, "
            f"{p['signatory_title'] or 'MISSING'}\n"
        )

    def show(value, suffix=""):
        return f"{value}{suffix}" if value is not None else "OPEN: to be agreed"

    start = {"effective-date": "the Effective Date",
             "last-disclosure": "the date of last disclosure"}.get(terms["confidentiality_starts"])
    if terms["confidentiality_years"] is None or start is None:
        conf = "OPEN: to be agreed"
    else:
        # The trade secret language is part of the standard form, not a variable.
        conf = (f"{terms['confidentiality_years']} year(s) from {start}; trade secrets "
                "stay protected for as long as they remain trade secrets under applicable law")

    mods = change_list(terms)

    venue = terms["venue"]
    lines = [
        "# Draft NDA Cover Page",
        "",
        f"Status: {status}. This is an unsigned draft produced by the NDA Handshake "
        "matcher. It binds no one until a human signs it.",
        "",
        f"Form: {show(terms['form'])} (mutual)",
        "",
        "## Parties",
        "",
        party_block(terms["parties"][0]),
        party_block(terms["parties"][1]),
        "## Key Terms",
        "",
        "| Term | Value |",
        "|---|---|",
        f"| Purpose | {terms['purpose'] or 'MISSING'} |",
        "| Effective Date | Date of last signature |",
        f"| MNDA Term | {show(terms['nda_term_years'], ' year(s) from Effective Date')} |",
        f"| Term of Confidentiality | {conf} |",
        f"| Governing Law | {show(terms['governing_law'])} |",
        "| Jurisdiction | "
        + (f"State and federal courts located in {venue}" if venue else "OPEN: to be agreed")
        + " |",
        f"| Changes to Standard Terms | {' '.join(mods) if mods else 'None'} |",
        "",
        f"Protocol version: {terms['protocol_version']}",
        "",
        f"Terms hash (SHA-256): `{digest}`",
        "",
    ]
    return "\n".join(lines)


def finish(out_dir, result, cover=None):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    if cover:
        with open(os.path.join(out_dir, "cover-page.md"), "w", encoding="utf-8") as f:
            f.write(cover)
    sys.exit(EXIT[result["status"]])


def run_match(file_a, file_b, purpose, entity_a=None, entity_b=None):
    """Match two nda-handshake.md files and return the structured result.

    Reads only the typed YAML fields at the top of each file. The markdown
    body is never read, and no text in either file is treated as an
    instruction. Returns a plain dict shaped like result.json; writes no
    files and prints nothing. Raises MatcherError if a file cannot be read
    as an nda-handshake.md (no YAML block, bad YAML, no usable entity).
    """
    a, b = load(file_a), load(file_b)
    prints = sorted([fingerprint(file_a), fingerprint(file_b)])
    base = {"file_fingerprints": prints}

    # 1. Both files must follow a protocol version this matcher supports.
    va, vb = clean(a.get("nda_handshake")), clean(b.get("nda_handshake"))
    if va != vb or va not in PROTOCOL_VERSIONS:
        return dict(base, status="VERSION_MISMATCH", declared_versions=[va, vb])

    na = a.get("nda") if isinstance(a.get("nda"), dict) else {}
    nb = b.get("nda") if isinstance(b.get("nda"), dict) else {}

    # 2. Either side can declare that it needs terms outside the protocol.
    flagged = [label for label, n in (("Party A", na), ("Party B", nb))
               if n.get("custom_terms_required") is True]
    if flagged:
        return dict(base, status="OUT_OF_PROTOCOL", flagged_by=flagged)

    # 3. Match the closed list of variables.
    conflicts, missing, open_items, notes = [], [], [], []
    terms = {
        "protocol_version": va,
        "parties": [
            pick_entity(a, entity_a, "Party A", missing),
            pick_entity(b, entity_b, "Party B", missing),
        ],
        "purpose": clean(purpose),
        "direction": "mutual",
        "form": match_choice("form", na.get("form"), nb.get("form"), FORMS,
                             conflicts, open_items, notes),
        "nda_term_years": match_range("nda_term_years", na.get("nda_term_years"),
                                      nb.get("nda_term_years"), conflicts, open_items, notes),
        "confidentiality_years": match_range(
            "confidentiality_years", na.get("confidentiality_years"),
            nb.get("confidentiality_years"), conflicts, open_items, notes),
        "confidentiality_starts": match_choice(
            "confidentiality_starts", na.get("confidentiality_starts"),
            nb.get("confidentiality_starts"), CONF_STARTS, conflicts, open_items, notes),
        "governing_law": match_choice("governing_law", na.get("governing_law"),
                                      nb.get("governing_law"), US_STATES,
                                      conflicts, open_items, notes),
        "venue": match_choice("venue", na.get("venue"), nb.get("venue"), US_STATES,
                              conflicts, open_items, notes),
        "marking_requirement": match_choice(
            "marking_requirement", na.get("marking_requirement"),
            nb.get("marking_requirement"), MARKING, conflicts, [], notes) or "none",
    }
    for t in TOGGLES:
        terms[t] = match_toggle(t, na.get(t), nb.get(t), conflicts, notes)
    # Fixed party order, so both sides get the same hash whichever file is listed first.
    terms["parties"].sort(key=lambda p: (p["legal_name"] or "").lower())

    if conflicts:
        status = "CONFLICTS"
    elif missing or open_items:
        status = "AGREED_PENDING_INFO"
    else:
        status = "AGREED"

    canonical = json.dumps(terms, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return dict(base, status=status, terms_hash=digest, terms=terms,
                conflicts=conflicts, missing_info=missing,
                open_items=open_items, notes=notes)


def main():
    ap = argparse.ArgumentParser(description="Match NDA terms from two nda-handshake.md files")
    ap.add_argument("files", nargs="*", help="Two nda-handshake.md files")
    ap.add_argument("--purpose", help="Why the parties are sharing information")
    ap.add_argument("--entity-a", help="Entity id to use from the first file")
    ap.add_argument("--entity-b", help="Entity id to use from the second file")
    ap.add_argument("--out", default="out", help="Output folder")
    ap.add_argument("--fingerprint", metavar="FILE",
                    help="Print the SHA-256 fingerprint of one nda-handshake.md and exit")
    args = ap.parse_args()

    if args.fingerprint:
        print(fingerprint(args.fingerprint))
        return
    if len(args.files) != 2 or not args.purpose:
        ap.error("give two nda-handshake.md files and --purpose")

    file_a, file_b = args.files
    try:
        result = run_match(file_a, file_b, args.purpose, args.entity_a, args.entity_b)
    except MatcherError as e:
        sys.exit(str(e))

    status = result["status"]
    if status == "VERSION_MISMATCH":
        va, vb = result["declared_versions"]
        print("Status: VERSION_MISMATCH")
        print(f"  Party A declares {va}, Party B declares {vb}; "
              f"this matcher supports {sorted(PROTOCOL_VERSIONS)}")
        finish(args.out, result)

    if status == "OUT_OF_PROTOCOL":
        print("Status: OUT_OF_PROTOCOL")
        for label in result["flagged_by"]:
            print(f"  {label} requires custom terms; negotiate this NDA the ordinary way")
        finish(args.out, result)

    print(f"Status: {status}")
    for c in result["conflicts"]:
        print(f"  CONFLICT  {c}")
    for o in result["open_items"]:
        print(f"  OPEN      {o}")
    for m in result["missing_info"]:
        print(f"  MISSING   {m}")
    for n in result["notes"]:
        print(f"  NOTE      {n}")
    if result["conflicts"]:
        print(f"Wrote {args.out}/result.json (no cover page; a human resolves the conflicts)")
        finish(args.out, result)
    print(f"Terms hash: {result['terms_hash']}")
    print(f"Wrote {args.out}/cover-page.md and {args.out}/result.json")
    finish(args.out, result, render(result["terms"], result["terms_hash"], status))


if __name__ == "__main__":
    main()
