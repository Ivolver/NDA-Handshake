#!/usr/bin/env python3
"""Write a valid nda-handshake.md from a company's facts and NDA positions.

This is the onboarding step. An assistant gathers the company's facts and
positions (for example from the company's own past NDAs), passes them here
as plain structured values, and gets back the text of a file plus a check
report. The file cannot complete a handshake until a person with authority
to bind the company gives the standing confirmation for its positions
(with_confirmation). Nothing here gives that confirmation for anyone.

Only the values passed in are used. Each one is written as a quoted string
or a number, so nothing in a value can change the structure of the file.
"""
import datetime
import json
import re

from match import (FileText, MatcherError, PROTOCOL_VERSIONS, RANGES, TOGGLES,
                   check_file, confirmation_text_fingerprint, effective_positions,
                   exception_fingerprint, exception_text_fingerprint, load,
                   positions_fingerprint, usable_sent_from, widens)

CHOICES = ["form", "confidentiality_starts", "governing_law", "venue",
           "marking_requirement"]
ORDER = ["form", "nda_term_years", "confidentiality_years",
         "confidentiality_starts", "governing_law", "venue",
         "marking_requirement", "residuals", "affiliate_sharing"]
MAX_TEXT = 200

FACTS = [
    ("legal_name", "the company's full legal name"),
    ("entity_type", "the type of entity, for example corporation"),
    ("formed_in", "the state the company is formed in"),
    ("address", "the company's address"),
    ("signatory_name", "the name of the person who signs"),
    ("signatory_title", "the signer's title"),
    ("notices_email", "the email address for legal notices"),
]


def _text(value, name, problems):
    """One line of plain text, or None. Records a problem if it is unusable."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        problems.append(f"{name} must be text")
        return None
    value = " ".join(value.split())
    if any(ord(c) < 32 for c in value):
        problems.append(f"{name} contains characters that are not allowed")
        return None
    if len(value) > MAX_TEXT:
        problems.append(f"{name} is longer than {MAX_TEXT} characters")
        return None
    return value or None


def _q(value):
    """A value as a quoted YAML scalar (JSON strings are valid YAML)."""
    return json.dumps(value, ensure_ascii=False)


def _whole(value, name, problems):
    if isinstance(value, bool) or not isinstance(value, int):
        problems.append(f"{name} must be a whole number of years")
        return None
    return value


def _position_lines(positions, problems):
    lines = []
    unknown = sorted(set(positions) - set(ORDER))
    if unknown:
        problems.append("positions has fields the protocol does not have: "
                        + ", ".join(str(u)[:40] for u in unknown))
    for name in ORDER:
        if name not in positions:
            continue
        pos = positions[name]
        if name in TOGGLES:
            t = _text(pos, name, problems)
            if t:
                lines.append(f"  {name}: {_q(t)}")
        elif name in RANGES:
            if not isinstance(pos, dict) or set(pos) - {"prefer", "min", "max"}:
                problems.append(f"{name} must have only prefer, min and max")
                continue
            parts = []
            for key in ("prefer", "min", "max"):
                if key in pos:
                    n = _whole(pos[key], f"{name}.{key}", problems)
                    if n is not None:
                        parts.append(f"{key}: {n}")
            lines.append(f"  {name}: {{{', '.join(parts)}}}")
        else:
            if not isinstance(pos, dict) or set(pos) - {"prefer", "accept"}:
                problems.append(f"{name} must have only prefer and accept")
                continue
            lines.append(f"  {name}:")
            prefer = _text(pos.get("prefer"), f"{name}.prefer", problems)
            if prefer:
                lines.append(f"    prefer: {_q(prefer)}")
            accept = pos.get("accept")
            if accept is not None:
                if not isinstance(accept, list):
                    problems.append(f"{name}.accept must be a list")
                else:
                    items = [_text(a, f"{name}.accept", problems) for a in accept]
                    lines.append("    accept: [" + ", ".join(_q(i) for i in items if i) + "]")
    return lines


def build_file(facts, positions=None, use_default_positions=True,
               custom_terms_required=False, company_name=None, website=None):
    """Return {"content", "ready", "problems", "warnings", "check"}.

    facts: legal_name, entity_type, formed_in, address, signatory_name,
    signatory_title, notices_email. positions: the company's own positions,
    in the same shape as the nda block of an nda-handshake.md; any of the
    nine terms may be left out. use_default_positions: adopt the protocol's
    default positions for every term not stated.

    "ready" is True only if the file has every party fact and no value the
    protocol does not allow. "content" is None when the inputs themselves
    are unusable.
    """
    problems = []
    warnings = []
    positions = positions or {}
    if not isinstance(facts, dict):
        raise MatcherError("facts must be a set of named values")
    if not isinstance(positions, dict):
        raise MatcherError("positions must be a set of named values")

    f = {}
    for key, meaning in FACTS:
        f[key] = _text(facts.get(key), key, problems)
        if f[key] is None and not any(p.startswith(key + " ") for p in problems):
            problems.append(f"{key} is missing: {meaning}")
    company_name = _text(company_name, "company_name", problems)
    website = _text(website, "website", problems)
    position_lines = _position_lines(positions, problems)
    if any(f[key] is None for key, _ in FACTS):
        return {"content": None, "ready": False, "problems": problems,
                "warnings": warnings, "check": None}
    input_problems = bool(problems)

    version = sorted(PROTOCOL_VERSIONS)[-1]
    out = ["---", f"nda_handshake: {_q(version)}", ""]
    if company_name or website:
        out.append("company:")
        if company_name:
            out.append(f"  name: {_q(company_name)}")
        if website:
            out.append(f"  website: {_q(website)}")
        out.append("")
    out += ["entities:",
            "  - id: main",
            "    default: true",
            f"    legal_name: {_q(f['legal_name'])}",
            f"    entity_type: {_q(f['entity_type'])}",
            f"    formed_in: {_q(f['formed_in'])}",
            f"    address: {_q(f['address'])}",
            "",
            "signatory:",
            f"  name: {_q(f['signatory_name'])}",
            f"  title: {_q(f['signatory_title'])}",
            "",
            "notices:",
            f"  email: {_q(f['notices_email'])}",
            "",
            "nda:",
            f"  custom_terms_required: {'true' if custom_terms_required is True else 'false'}"]
    if use_default_positions:
        out.append("  profile: default")
    out += position_lines
    out += ["---", "", f"# {f['legal_name']}", "",
            f"NDA positions for {f['legal_name']} under the NDA Handshake "
            "protocol. Software reads only the block above.", ""]
    content = "\n".join(out)

    check = check_file(FileText(content))
    problems += [f"missing: {m}" for m in check["missing_party_facts"]]
    problems += check["bad_values"]
    if check["unstated_variables"]:
        warnings.append("No position stated for: "
                        + ", ".join(check["unstated_variables"])
                        + ". A handshake needs a position on every term.")
    if check["custom_terms_required"]:
        warnings.append("custom_terms_required is set, so every handshake "
                        "with this file ends as OUT_OF_PROTOCOL.")
    if input_problems:
        content = None
    return {"content": content, "ready": not problems, "problems": problems,
            "warnings": warnings, "check": check if content else None}


def without_confirmation(text):
    """A file's text with its confirmation block removed. Nothing else changes."""
    m = re.match(r"^(---\s*\n)(.*?)(\n---\s*(?:\n|$))", text, re.S)
    if not m:
        raise MatcherError("The file has no YAML block at the top")
    kept, skipping = [], False
    for line in m.group(2).split("\n"):
        if re.match(r"^confirmation\s*:", line):
            skipping = True
            continue
        if skipping and (line[:1] in (" ", "\t") or not line.strip()):
            continue                      # a line belonging to the block just removed
        skipping = False
        kept.append(line)
    while kept and not kept[-1].strip():
        kept.pop()
    return m.group(1) + "\n".join(kept) + m.group(3) + text[m.end():]


def with_confirmation(text, confirmed_by, sent_from, date=None):
    """A file's text with the standing confirmation recorded in it.

    confirmed_by is the name and title of the person who gave the
    confirmation, as they typed it. sent_from is the email domain the
    company sends its file from, or one full email address if the company
    uses a public email service. The block also records the fingerprint of the
    confirmation text and of the positions it was given for. Only the
    confirmation block changes; every other line is kept as it is.

    This records a confirmation a person has given. It must be called only
    after that person has read the confirmation text and typed their name.
    """
    problems = []
    confirmed_by = _text(confirmed_by, "confirmed_by", problems)
    sent_from = (_text(sent_from, "sent_from", problems) or "").lower()
    if problems or not confirmed_by:
        raise MatcherError("The confirmation needs the name and title of the person "
                           "giving it, as one line.")
    if not usable_sent_from(sent_from):
        raise MatcherError(
            "sent_from must be a domain the company controls, for example "
            "harbor.example, or one full email address. A public email service such "
            "as gmail.com is accepted only as a full address.")
    try:
        day = (datetime.date.fromisoformat(date) if date else datetime.date.today()).isoformat()
    except ValueError:
        raise MatcherError("The date must be written as YYYY-MM-DD.")
    base = without_confirmation(text)
    data = load(FileText(base))
    m = re.match(r"^(---\s*\n)(.*?)(\n---\s*(?:\n|$))", base, re.S)
    block = ["", "", "confirmation:",
             f"  confirmed_by: {_q(confirmed_by)}",
             f"  date: {_q(day)}",
             f"  sent_from: {_q(sent_from)}",
             f"  text: {_q(confirmation_text_fingerprint())}",
             f"  positions: {_q(positions_fingerprint(data))}"]
    out = m.group(1) + m.group(2) + "\n".join(block) + m.group(3) + base[m.end():]

    # Nothing but the confirmation may have changed, and it must read back as valid.
    after = load(FileText(out))
    rest = {key: value for key, value in after.items() if key != "confirmation"}
    if rest != data or not check_file(FileText(out))["confirmation"]["confirmed"]:
        raise MatcherError(
            "The confirmation could not be written into this file safely. "
            "Run check_file on the file and fix what it reports first.")
    return out


def with_exception(text, prior, approved_by, terms, date=None):
    """A company's file with a one-deal exception added, for a second round.

    prior is the first round's commitment. terms maps each excepted term to
    the wider position approved for this one NDA. approved_by is the name
    and title of the person who approved it, as they typed it. Only the
    exception block is added; the company's positions, its confirmation and
    every other line are kept as they are, so the standing confirmation
    still applies.

    This records an approval a person has given. It must be called only
    after that person has read the exception text and typed their name.
    """
    problems = []
    approved_by = _text(approved_by, "approved_by", problems)
    if problems or not approved_by:
        raise MatcherError("The exception needs the name and title of the person "
                           "approving it, as one line.")
    if not re.fullmatch(r"[0-9a-f]{64}", prior or ""):
        raise MatcherError("The exception needs the first round's commitment.")
    try:
        day = (datetime.date.fromisoformat(date) if date else datetime.date.today()).isoformat()
    except ValueError:
        raise MatcherError("The date must be written as YYYY-MM-DD.")
    data = load(FileText(text))
    if "exception" in data:
        raise MatcherError("The file already carries an exception.")
    standing = effective_positions(data)
    if not terms or not all(widens(name, standing.get(name), position)
                            for name, position in terms.items()):
        raise MatcherError("An exception may only widen the company's standing "
                           "position on a term.")
    m = re.match(r"^(---\s*\n)(.*?)(\n---\s*(?:\n|$))", text, re.S)
    if not m:
        raise MatcherError("The file has no YAML block at the top")
    block = ["", "", "exception:",
             f"  for: {_q(prior)}",
             f"  approved_by: {_q(approved_by)}",
             f"  date: {_q(day)}",
             f"  text: {_q(exception_text_fingerprint())}",
             "  terms:"]
    block += [f"    {name}: {_q(terms[name])}" for name in sorted(terms)]
    block += [f"  positions: {_q(exception_fingerprint(prior, terms))}"]
    out = m.group(1) + m.group(2).rstrip("\n") + "\n".join(block) + m.group(3) + text[m.end():]

    # Nothing but the exception may have changed, and it must read back as given.
    after = load(FileText(out))
    rest = {key: value for key, value in after.items() if key != "exception"}
    if rest != data or after["exception"].get("terms") != terms:
        raise MatcherError("The exception could not be written into this file safely.")
    return out
