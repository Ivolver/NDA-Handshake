#!/usr/bin/env python3
"""Write a valid nda-handshake.md from a company's facts and NDA positions.

This is the onboarding step. An assistant gathers the company's facts and
positions (for example from the company's own past NDAs), passes them here
as plain structured values, and gets back the text of a file plus a check
report. A human must confirm the positions before the file is sent to
anyone.

Only the values passed in are used. Each one is written as a quoted string
or a number, so nothing in a value can change the structure of the file.
"""
import json

from match import (FileText, MatcherError, PROTOCOL_VERSIONS, RANGES, TOGGLES,
                   check_file)

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
                        + ". The company will accept any allowed value for these.")
    if check["custom_terms_required"]:
        warnings.append("custom_terms_required is set, so every handshake "
                        "with this file ends as OUT_OF_PROTOCOL.")
    if input_problems:
        content = None
    return {"content": content, "ready": not problems, "problems": problems,
            "warnings": warnings, "check": check if content else None}
