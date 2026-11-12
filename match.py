#!/usr/bin/env python3
"""company.md NDA matcher, v0.1

Reads two company.md files, intersects their NDA positions, and writes
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

MAX_LEN = 200
RIDERS = ["residuals", "affiliate_sharing", "non_solicit"]
RIDER_POSITIONS = {"require", "accept", "reject"}


def load(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*(\n|$)", text, re.S)
    if not m:
        sys.exit(f"{path}: no YAML block found at the top of the file")
    data = yaml.safe_load(m.group(1))
    if not isinstance(data, dict):
        sys.exit(f"{path}: YAML block is not a set of fields")
    return data


def clean(value):
    """Return a short single-line string, or None if missing or a TODO."""
    if value is None:
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
        sys.exit(f"{label}: no entities listed")
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
            sys.exit(f"{label}: no entity with id '{entity_id}'")
        chosen = entities[0]
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


def match_range(name, a, b, conflicts):
    try:
        lo = max(int(a["min"]), int(b["min"]))
        hi = min(int(a["max"]), int(b["max"]))
        target = (int(a["prefer"]) + int(b["prefer"])) / 2
    except (KeyError, TypeError, ValueError):
        conflicts.append(f"{name}: one side has no valid min / max / prefer")
        return None
    if lo > hi:
        conflicts.append(
            f"{name}: ranges do not overlap "
            f"({a['min']} to {a['max']} vs {b['min']} to {b['max']})"
        )
        return None
    # Midpoint of the two preferences, rounded half up, kept inside the overlap.
    return max(lo, min(hi, int(target + 0.5)))


def ranked(pos):
    """Preferred value first, then the rest of the accept list, de-duplicated."""
    if not isinstance(pos, dict):
        return []
    items = [pos.get("prefer")] + list(pos.get("accept") or [])
    out = []
    for item in items:
        s = clean(item)
        if s and s.lower() not in [o.lower() for o in out]:
            out.append(s)
    return out


def match_choice(name, a, b, conflicts):
    ra, rb = ranked(a), ranked(b)
    lower_b = [x.lower() for x in rb]
    common = [x for x in ra if x.lower() in lower_b]
    if not common:
        conflicts.append(f"{name}: no common option ({ra} vs {rb})")
        return None
    # Lowest combined rank wins; alphabetical order breaks ties.
    return min(common, key=lambda x: (ra.index(x) + lower_b.index(x.lower()), x))


def match_rider(name, a, b, conflicts):
    pa = clean(a) or "accept"
    pb = clean(b) or "accept"
    if pa not in RIDER_POSITIONS or pb not in RIDER_POSITIONS:
        conflicts.append(f"rider {name}: position must be require, accept or reject")
        return False
    if {pa, pb} == {"require", "reject"}:
        conflicts.append(f"rider {name}: one side requires it, the other rejects it")
        return False
    return "require" in (pa, pb)


def render(terms, digest, status):
    p1, p2 = terms["parties"]

    def party_block(p):
        return (
            f"**{p['legal_name'] or 'MISSING'}**, a {p['formed_in'] or 'MISSING'} "
            f"{p['entity_type'] or 'MISSING'}\n\n"
            f"- Address: {p['address'] or 'MISSING'}\n"
            f"- Notice email: {p['notice_email'] or 'MISSING'}\n"
            f"- Signatory: {p['signatory_name'] or 'MISSING'}, "
            f"{p['signatory_title'] or 'MISSING'}\n"
        )

    riders = terms["riders_included"]
    lines = [
        "# Draft NDA Cover Page",
        "",
        f"Status: {status}. This is an unsigned draft produced by the company.md "
        "matcher. It binds no one until a human signs it.",
        "",
        f"Form: {terms['form']}",
        "",
        "## Parties",
        "",
        party_block(p1),
        party_block(p2),
        "## Key Terms",
        "",
        "| Term | Value |",
        "|---|---|",
        f"| Type | {terms['type']} |",
        f"| Purpose | {terms['purpose'] or 'MISSING'} |",
        "| Effective Date | Date of last signature |",
        f"| MNDA Term | {terms['nda_term_years']} year(s) from Effective Date |",
        f"| Term of Confidentiality | {terms['confidentiality_years']} year(s) "
        "from Effective Date |",
        f"| Governing Law | {terms['governing_law']} |",
        f"| Jurisdiction | State and federal courts located in {terms['venue']} |",
        f"| Modifications | {', '.join(riders) if riders else 'None'} |",
        "",
        f"Terms hash (SHA-256): `{digest}`",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Match NDA terms from two company.md files")
    ap.add_argument("file_a")
    ap.add_argument("file_b")
    ap.add_argument("--purpose", required=True, help="Why the parties are sharing information")
    ap.add_argument("--entity-a", help="Entity id to use from file A (default entity if omitted)")
    ap.add_argument("--entity-b", help="Entity id to use from file B (default entity if omitted)")
    ap.add_argument("--out", default="out", help="Output folder")
    args = ap.parse_args()

    a, b = load(args.file_a), load(args.file_b)
    na = a.get("nda") if isinstance(a.get("nda"), dict) else {}
    nb = b.get("nda") if isinstance(b.get("nda"), dict) else {}
    conflicts, missing = [], []

    terms = {
        "parties": [
            pick_entity(a, args.entity_a, "Party A", missing),
            pick_entity(b, args.entity_b, "Party B", missing),
        ],
        "purpose": clean(args.purpose),
        "form": match_choice("form", na.get("form"), nb.get("form"), conflicts),
        "type": match_choice("type", na.get("type"), nb.get("type"), conflicts),
        "nda_term_years": match_range(
            "nda_term_years", na.get("nda_term_years") or {}, nb.get("nda_term_years") or {}, conflicts),
        "confidentiality_years": match_range(
            "confidentiality_years", na.get("confidentiality_years") or {},
            nb.get("confidentiality_years") or {}, conflicts),
        "governing_law": match_choice(
            "governing_law", na.get("governing_law"), nb.get("governing_law"), conflicts),
        "venue": match_choice("venue", na.get("venue"), nb.get("venue"), conflicts),
    }
    # Fixed party order, so both sides get the same hash whichever file is listed first.
    terms["parties"].sort(key=lambda p: (p["legal_name"] or "").lower())
    ra = na.get("riders") if isinstance(na.get("riders"), dict) else {}
    rb = nb.get("riders") if isinstance(nb.get("riders"), dict) else {}
    terms["riders_included"] = [
        r for r in RIDERS if match_rider(r, ra.get(r), rb.get(r), conflicts)
    ]

    if conflicts:
        status = "CONFLICTS"
    elif missing:
        status = "AGREED_PENDING_INFO"
    else:
        status = "AGREED"

    canonical = json.dumps(terms, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    os.makedirs(args.out, exist_ok=True)
    result = {"status": status, "terms_hash": digest, "terms": terms,
              "conflicts": conflicts, "missing_info": missing}
    with open(os.path.join(args.out, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Status: {status}")
    for c in conflicts:
        print(f"  CONFLICT  {c}")
    for m in missing:
        print(f"  MISSING   {m}")
    if not conflicts:
        with open(os.path.join(args.out, "cover-page.md"), "w", encoding="utf-8") as f:
            f.write(render(terms, digest, status))
        print(f"Terms hash: {digest}")
        print(f"Wrote {args.out}/cover-page.md and {args.out}/result.json")
    else:
        print(f"Wrote {args.out}/result.json (no cover page; a human resolves the conflicts)")
    sys.exit(1 if conflicts else 0)


if __name__ == "__main__":
    main()
