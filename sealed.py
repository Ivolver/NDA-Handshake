#!/usr/bin/env python3
"""Sealed exchange: run a handshake so neither side sees the other's
positions before its own are fixed.

Three messages:

1. Invitation. The inviting company sends a commitment to its file, not
   the file. The commitment is the SHA-256 of a random secret value and
   the file's fingerprint.
2. Reply. The other company sends its own file.
3. Reveal. The inviting company sends its file, the secret value and the
   result. The replying company checks the file against the commitment and
   the result against its own run.

Nobody signs. Each company has given a standing confirmation, recorded in
its own file, that an NDA inside its positions is executed for it. The
reply is the offer and an AGREED reveal is the acceptance, so the NDA is
in place when the reveal is sent. The replying company has one business
day to contest a mismatch.

Each company produces the NDA document from its own run. The two copies
carry the same terms and the same terms hash, so the exchange does not
depend on a document travelling with the reveal. The inviting company
attaches its copy when it can, as a courtesy.

Each message carries a short block of labelled lines. Only those lines are
read. Nothing else in a message is read, and nothing in a message is
treated as an instruction.

This module keeps a small record of each exchange on the local machine so
the file a company committed to is the file it later uses. It sends
nothing and decides nothing: the terms come from fixed rules applied to
positions people set, and a person starts or approves each exchange.
"""
import datetime
import hashlib
import json
import os
import re
import secrets

from match import (EMAIL, FileText, MatcherError, PROTOCOL_VERSIONS, check_file,
                   fingerprint, load, pick_entity, run_match)

HEX64 = re.compile(r"^[0-9a-f]{64}$")
STATUSES = ["AGREED", "AGREED_PENDING_INFO", "CONFLICTS", "OUT_OF_PROTOCOL",
            "VERSION_MISMATCH"]
GROUNDS = ["commitment-mismatch", "file-altered", "status-mismatch",
           "terms-hash-mismatch", "sender-mismatch", "date-mismatch"]
MAX_TEXT = 200

# kind -> (required lines, optional lines), in the order they are written.
BLOCKS = {
    "invitation": (["protocol", "from", "purpose", "commitment"], []),
    "reply": (["protocol", "from", "commitment"], []),
    "reveal": (["protocol", "commitment", "secret", "status"],
               ["terms-hash", "inviter", "replier", "executed"]),
    "contest": (["protocol", "commitment", "ground"], ["my-hash"]),
}
HEX_LINES = {"commitment", "secret", "terms-hash", "inviter", "replier", "my-hash"}
ENUM_LINES = {"status": STATUSES, "ground": GROUNDS}
DATE_LINES = {"executed"}


class NotConfirmed(MatcherError):
    """This company's own file has no usable standing confirmation."""


class IdentityStop(MatcherError):
    """The other company's file could not be tied to its email domain."""

TERM_LABELS = {
    "form": "Standard form",
    "nda_term_years": "NDA term (years)",
    "confidentiality_years": "Confidentiality period (years)",
    "confidentiality_starts": "Confidentiality period starts from",
    "governing_law": "Governing law",
    "venue": "Venue",
    "marking_requirement": "Marking requirement",
    "residuals": "Residuals clause",
    "affiliate_sharing": "Affiliate sharing",
}


# ---------------------------------------------------------------- local records

def home():
    """Folder for settings and exchange records on this machine."""
    return os.environ.get("NDA_HANDSHAKE_HOME") or os.path.join(
        os.path.expanduser("~"), ".nda-handshake")


def _write_private(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def read_settings():
    try:
        with open(os.path.join(home(), "settings.json"), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(storage_folder):
    folder = os.path.abspath(os.path.expanduser(storage_folder))
    os.makedirs(folder, exist_ok=True)
    _write_private(os.path.join(home(), "settings.json"), {"storage_folder": folder})
    return folder


def installer_storage_folder():
    """The storage folder chosen when the connector was installed, if any.

    A one-click install asks the person for the folder and passes it in the
    NDA_HANDSHAKE_STORAGE environment variable.
    """
    folder = (os.environ.get("NDA_HANDSHAKE_STORAGE") or "").strip()
    if not folder or "${" in folder:
        return None
    return os.path.abspath(os.path.expanduser(folder))


def storage_folder():
    chosen = installer_storage_folder()
    if chosen:
        os.makedirs(chosen, exist_ok=True)
        return chosen
    folder = read_settings().get("storage_folder")
    return folder if isinstance(folder, str) and folder else None


def own_file_path():
    folder = storage_folder()
    return os.path.join(folder, "nda-handshake.md") if folder else None


def _record_path(role, commitment):
    return os.path.join(home(), "exchanges", f"{role}-{commitment}.json")


def _save_record(role, commitment, data):
    _write_private(_record_path(role, commitment), data)


def _load_record(role, commitment):
    try:
        with open(_record_path(role, commitment), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        what = "invitation" if role == "inviter" else "reply"
        raise MatcherError(
            f"No {what} with this commitment was made on this machine, so "
            "this message cannot be processed here.")


# ------------------------------------------------------------- message blocks

def _one_line(value, name):
    value = " ".join(str(value).split())
    if not value or len(value) > MAX_TEXT or any(ord(c) < 32 for c in value):
        raise MatcherError(f"{name} must be one line of at most {MAX_TEXT} characters")
    return value


def format_block(kind, fields):
    required, optional = BLOCKS[kind]
    lines = [f"nda-handshake: {kind}"]
    for key in required + optional:
        if key in fields and fields[key] is not None:
            lines.append(f"{key}: {fields[key]}")
        elif key in required:
            raise MatcherError(f"{kind} block needs a {key} line")
    return "\n".join(lines) + "\n"


def parse_block(text, kind):
    """Read the labelled lines of one message block out of an email's text.

    Only the block is read. A line is used only if its label belongs to
    this kind of message and its value has the expected form.
    """
    if not isinstance(text, str) or len(text) > 200_000:
        raise MatcherError("The message text is missing or too long")
    required, optional = BLOCKS[kind]
    known = set(required + optional)
    lines = [re.sub(r"^[>\s]+", "", ln).rstrip() for ln in text.splitlines()]
    start = None
    for i, ln in enumerate(lines):
        if re.fullmatch(r"nda-handshake:\s*" + kind, ln, re.I):
            start = i
            break
    if start is None:
        raise MatcherError(f"No 'nda-handshake: {kind}' block found in the message")
    fields, last = {}, None
    for ln in lines[start + 1:]:
        if not ln:
            break
        m = re.match(r"^([a-z-]+):\s*(.*)$", ln)
        if m and m.group(1) in known:
            last = m.group(1)
            if last in fields:
                raise MatcherError(f"The {kind} block has two {last} lines")
            fields[last] = m.group(2)
        elif last in ("from", "purpose"):
            fields[last] += " " + ln      # a long line wrapped by an email program
        else:
            break
    for key in required:
        if key not in fields:
            raise MatcherError(f"The {kind} block has no {key} line")
    out = {}
    for key, value in fields.items():
        value = value.strip()
        if key in HEX_LINES:
            if not HEX64.match(value):
                raise MatcherError(f"The {key} line is not a 64-character fingerprint")
        elif key in ENUM_LINES:
            if value not in ENUM_LINES[key]:
                raise MatcherError(f"The {key} line has a value the protocol does not allow")
        elif key in DATE_LINES:
            try:
                value = datetime.date.fromisoformat(value).isoformat()
            except ValueError:
                raise MatcherError(f"The {key} line is not a date written as YYYY-MM-DD")
        else:
            value = _one_line(value, key)
        out[key] = value
    if out["protocol"] not in PROTOCOL_VERSIONS:
        raise MatcherError(
            f"The message uses protocol version {out['protocol'][:20]}, which this "
            f"software does not support (supported: {', '.join(sorted(PROTOCOL_VERSIONS))})")
    return out


def commitment_for(secret, file_fingerprint):
    return hashlib.sha256(f"{secret}\n{file_fingerprint}".encode("ascii")).hexdigest()


# ------------------------------------------------------------------- helpers

def _protocol():
    return sorted(PROTOCOL_VERSIONS)[-1]


def _own_text(own_source, need_confirmation=True):
    """This company's own file, checked as ready to use.

    Returns (text, path). The path is None if the file was given as text.
    A handshake needs the company's standing confirmation; reading the
    company's positions for a summary or an ordinary draft does not.
    """
    path = None
    if own_source is None:
        path = own_file_path()
        if not path or not os.path.isfile(path):
            raise MatcherError(
                "This company has no nda-handshake.md yet. Run setup, then "
                "draft_file, or give the file directly.")
        own_source = path
    if isinstance(own_source, FileText):
        text = str(own_source)
    else:
        path = os.path.abspath(own_source)
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    report = check_file(FileText(text))
    problems = [f"missing: {m}" for m in report["missing_party_facts"]] + report["bad_values"]
    if not report["protocol_version_supported"]:
        problems.append(
            "the file's protocol version is not supported. If it says 0.6 or earlier, "
            f"change its nda_handshake line to \"{_protocol()}\" and then give the "
            "confirmation this version needs")
    if problems:
        raise MatcherError("This company's own file is not ready: " + "; ".join(problems))
    if need_confirmation and not report["confirmation"]["ready"]:
        raise NotConfirmed(
            "This company has not given the confirmation a handshake needs: "
            + "; ".join(p.replace("Party: ", "") for p in report["confirmation"]["problems"]))
    return text, path


def _legal_name(text):
    return pick_entity(load(FileText(text)), None, "Party", [])["legal_name"] or "Unknown"


def positions_summary(source):
    """This file's own position on each term, in plain English."""
    result = run_match(source, source, "summary", require_confirmation=False)
    if "summary" not in result:
        return []
    return [{"term": e["term"], "label": TERM_LABELS.get(e["term"], e["term"]),
             "position": e["a"]} for e in result["summary"]["terms"]]


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "counterparty"


def _deal_folder(out_dir, counterparty, commitment, base=None):
    """Where one deal's files go: out_dir if given, otherwise a "deals"
    folder beside the own file used for the exchange, otherwise under the
    storage folder."""
    if out_dir:
        if "://" in out_dir:
            raise MatcherError("out_dir must be a local folder")
        folder = os.path.abspath(os.path.expanduser(out_dir))
    else:
        base = base or storage_folder()
        if not base:
            raise MatcherError(
                "No storage folder is set. Run setup first, or give out_dir.")
        folder = os.path.join(base, "deals", "-".join(
            [datetime.date.today().isoformat(), _slug(counterparty), commitment[:8]]))
    os.makedirs(folder, exist_ok=True)
    return folder


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


BLANK_PARTY = {
    "legal_name": "[Counterparty legal name]", "entity_type": "[entity type]",
    "formed_in": "[state of formation]", "address": "[address]",
    "signatory_name": "[name]", "signatory_title": "[title]",
    "notice_email": "[email for notices]",
}


def ordinary_draft(purpose, own_source=None, counterparty_name=None):
    """The terms of an ordinary draft: this company's own preferred positions.

    For a counterparty that does not use NDA Handshake and asks for a draft
    the usual way. No handshake is involved, so there is no terms hash.
    """
    purpose = _one_line(purpose, "purpose")
    text, _ = _own_text(own_source, need_confirmation=False)
    result = run_match(FileText(text), FileText(text), purpose, require_confirmation=False)
    if result.get("status") != "AGREED":
        raise MatcherError(
            "An ordinary draft cannot be made from this company's file: " + (
                "it says custom terms are required."
                if result.get("status") == "OUT_OF_PROTOCOL" else
                "it does not state a usable position on every term."))
    terms = dict(result["terms"])
    own = terms["parties"][0]
    other = dict(BLANK_PARTY)
    if counterparty_name:
        other["legal_name"] = _one_line(counterparty_name, "counterparty")
    terms["parties"] = [own, other]
    return {"terms": terms, "own_name": own["legal_name"],
            "positions": positions_summary(FileText(text))}


def draft_email(own_name):
    """The email that goes with an ordinary draft. It has no block for assistants."""
    return "\n".join([
        "Hello,", "",
        "Of course. A draft mutual NDA is attached.", "",
        "It is the Common Paper Mutual NDA, a standard form that is free to use. The",
        f"standard terms are unchanged, and the choices on the cover page are {own_name}'s",
        "usual positions. Mark it up as you would any draft, or tell us it works and we",
        "will both sign.", ""])


def conflict_report(result, own_name):
    """What failed, and a suggestion for this company's own human.

    The suggestion is addressed only to this company. It is never sent to
    the other side, and nothing changes unless a person decides it should.
    """
    status = result.get("status")
    if status == "VERSION_MISMATCH":
        return {"status": status, "explanation":
                "The two files follow different protocol versions, or a version "
                "this software does not support.", "failed_terms": []}
    if status == "OUT_OF_PROTOCOL":
        return {"status": status, "explanation":
                "One side needs terms the protocol does not cover. Negotiate "
                "this NDA the ordinary way.", "failed_terms": []}
    summary = result.get("summary") or {"terms": []}
    mine, theirs = ("a", "b") if summary.get("party_a") == own_name else ("b", "a")
    failed = []
    for e in summary["terms"]:
        if e.get("outcome") != "CONFLICT":
            continue
        yours, other = e[mine], e[theirs]
        suggestion = ("Decide whether you could move to one of their positions "
                      "for this deal only.")
        nums = re.search(r"accepts (\d+)(?: to (\d+))?", other)
        if e["term"] in ("residuals", "affiliate_sharing"):
            suggestion = ("One side requires this clause and the other rejects it. "
                          "Decide whether you could change your position to "
                          "'accept' for this deal only, or ask them to.")
        elif nums and e["term"].endswith("_years"):
            lo, hi = int(nums.group(1)), int(nums.group(2) or nums.group(1))
            mine_nums = re.search(r"accepts (\d+)(?: to (\d+))?", yours)
            if mine_nums:
                my_hi = int(mine_nums.group(2) or mine_nums.group(1))
                nearest = lo if my_hi < lo else hi
                gap = "above" if my_hi < lo else "below"
                suggestion = (f"Their range is entirely {gap} yours. The nearest "
                              f"value they accept is {nearest}. Decide whether you "
                              f"could accept {nearest} for this deal only.")
        else:
            suggestion = ("No option is acceptable to both. Decide whether you "
                          "could accept one of their options for this deal only.")
        failed.append({"term": e["term"], "label": TERM_LABELS.get(e["term"], e["term"]),
                       "your_position": yours, "their_position": other,
                       "suggestion": suggestion})
    return {"status": status,
            "explanation": "The two files do not produce an agreement on every term."
            if failed else "The positions line up, but something an NDA needs is missing. "
            "Nothing is executed.",
            "failed_terms": failed,
            "missing_info": result.get("missing_info", []),
            "open_items": result.get("open_items", []),
            "how_to_proceed":
                "Show this to a person at your company. If they approve changed "
                "positions for this deal only, start a new sealed exchange with "
                "the changed file. Assistants do not bargain with each other."}


# ------------------------------------------------- the emails people read

DIVIDER = "--- for the assistants (please leave this part as it is) ---"
PROJECT_URL = "https://github.com/Ivolver/NDA-Handshake"
# The page a person who receives an invitation is sent to.
INVITED_URL = "https://ultravireslabs.com/nda-handshake"
MARKING_WORDS = {
    "none": "none",
    "written-marked": "written information must be marked confidential",
    "written-marked-oral-confirmed":
        "written information must be marked; oral information confirmed in writing",
}
STARTS_WORDS = {"effective-date": "the effective date",
                "last-disclosure": "the last disclosure"}


def _email(lines, block):
    """The part for people, then the block the software reads, last."""
    return "\n".join(["Hello,", ""] + lines + ["", DIVIDER, block])


def _years(n):
    return f"{n} year" if n == 1 else f"{n} years"


def terms_lines(terms):
    """The agreed terms as short plain lines."""
    law, venue = terms.get("governing_law"), terms.get("venue")
    out = [f"  NDA term: {_years(terms.get('nda_term_years'))}",
           f"  Confidentiality period: {_years(terms.get('confidentiality_years'))} from "
           + STARTS_WORDS.get(terms.get("confidentiality_starts"),
                              str(terms.get("confidentiality_starts")))]
    if law == venue:
        out.append(f"  Governing law and venue: {law}")
    else:
        out += [f"  Governing law: {law}", f"  Venue: {venue}"]
    out += [f"  Marking requirement: "
            + MARKING_WORDS.get(terms.get("marking_requirement"),
                                str(terms.get("marking_requirement"))),
            "  Residuals clause: " + ("included" if terms.get("residuals") else "not included"),
            "  Affiliate sharing: "
            + ("included" if terms.get("affiliate_sharing") else "not included")]
    return out


def invitation_email(own_name, purpose, block):
    subject = f"\U0001F91D NDA Handshake: {own_name} would like to put an NDA in place"
    return subject, _email([
        f"Before we get into the details, {own_name} would like to put a mutual NDA",
        "in place. We use NDA Handshake, an open protocol that lets our assistants",
        "settle a standard NDA so nobody has to trade redlines.",
        "",
        f"What we would like to discuss: {purpose}",
        "",
        "How it works:",
        "  1. Our NDA positions are already locked in, sealed in the code below.",
        "  2. Your assistant replies with your positions.",
        "  3. We open ours, and both assistants work out the same NDA.",
        "",
        "Neither side sees the other's positions first, so there is no peeking and",
        "no haggling. If the positions meet, the NDA is in place right then. Nobody",
        "has to sign anything, because each company approves its positions in",
        "advance. If your assistant already knows NDA Handshake, just ask it to",
        "handle this email.",
        "",
        "Not sure what to do? Ask your AI assistant to read this email and the",
        "page below, and to walk you through it. You have two easy options:",
        "",
        "  - Just reply \"please send a draft\" and we will send an ordinary NDA the",
        "    usual way. That takes ten seconds.",
        "  - Or try the handshake. The page below explains it in plain words. The",
        "    first time takes about fifteen minutes and needs someone who can approve",
        "    NDAs for your company. After that it takes about a minute.",
        "",
        f"What this is and what to do next: {INVITED_URL}",
    ], block)


def reply_email(own_name, block):
    return _email([
        f"Happy to shake on it. {own_name}'s NDA positions are attached.",
        "",
        "Your move: once your assistant opens your sealed positions, both sides",
        "will see the same result. If our positions meet, the NDA is in place when",
        "your assistant sends that result.",
    ], block)


def reveal_email(result, block):
    status = result.get("status")
    if status == "AGREED":
        lines = ["We have a handshake. Here is what our two sets of positions produced:", ""]
        lines += terms_lines(result["terms"])
        lines += ["",
                  "You do not have to take our word for it. Our positions are attached, and",
                  "your assistant will check them against the seal and run the numbers itself.",
                  "",
                  "This NDA has been executed by both companies and is in place as of this",
                  "email. Each company approved its positions in advance, so both signatures",
                  "are already on it and nobody needs to sign by hand. If your assistant's",
                  "check does not come out the same as ours, it should tell us within one",
                  "business day. The executed NDA is attached if our assistant was able to",
                  "attach it, and your assistant produces an identical copy."]
    elif status == "CONFLICTS":
        failed = [TERM_LABELS.get(e["term"], e["term"]).replace(" (years)", "")
                  for e in (result.get("summary") or {}).get("terms", [])
                  if e.get("outcome") == "CONFLICT"]
        lines = ["No handshake this time. Our positions and yours did not meet on:", ""]
        lines += [f"  {label}" for label in failed]
        lines += ["",
                  "Our positions are attached, as promised, so your side can see the same",
                  "result. If someone on your team would like to talk it through, just reply.",
                  "Humans are still allowed to negotiate."]
    else:
        why = {"AGREED_PENDING_INFO":
               "Our positions line up, but something needed for the NDA is missing: a\n"
               "company detail, a position, or a company's confirmation.",
               "OUT_OF_PROTOCOL":
               "One of us needs terms that NDA Handshake does not cover.",
               "VERSION_MISMATCH":
               "Our files follow different versions of the protocol."}.get(status, "")
        lines = ["No handshake yet. " + why, "",
                 "Our positions are attached, as promised, so your side can see the same",
                 "result. This one is best finished by people, so just reply to this email."]
    return _email(lines, block)


def contest_email(block):
    return _email([
        "Our check of your reveal did not come out the same as yours, so no NDA is",
        "in place between us from this exchange. Could someone on your side take a",
        "look? The details for your assistant are below.",
    ], block)


# ------------------------------------------------- identity and execution

def nice_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d:%B} {d.day}, {d.year}"


def sender_address(sender):
    """The bare address an email came from, in lower case, or None.

    Accepts "name@host" or "Name <name@host>".
    """
    if not isinstance(sender, str):
        return None
    m = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)\s*>?\s*$", sender.strip()[:320])
    address = m.group(1).lower().rstrip(".") if m else ""
    return address if EMAIL.match(address) else None


def _their_confirmation(result, own_fingerprint):
    """The other company's entry in a result's confirmation record, or None."""
    entries = result.get("confirmations") or []
    own = next((c for c in entries if c["file_fingerprint"] == own_fingerprint), None)
    return next((c for c in entries if c is not own), None)


def sender_problem(confirmation, sender):
    """Why an email cannot be tied to the company whose file it carried, or None.

    A company's file says where it is sent from: a domain the company
    controls, or one full email address. The file counts as that company's
    only if the email came from that address, or from an address at that
    domain or a subdomain of it.
    """
    wanted = (confirmation or {}).get("sent_from")
    if not wanted:
        return None                       # no confirmation, so nothing can be executed
    address = sender_address(sender)
    if not address:
        return ("the address the email came from was not given, so the file could "
                f"not be tied to {wanted}, where the file says it is sent from")
    host = address.rsplit("@", 1)[1]
    ok = (address == wanted if "@" in wanted
          else host == wanted or host.endswith("." + wanted))
    if not ok:
        return (f"the email came from {address}, not from {wanted}, where the file "
                "says it is sent from")
    return None


def signing(result, executed):
    """For the NDA document: each company's electronic execution details."""
    return {c["party"]: {"date": executed, "confirmed_by": c["confirmed_by"],
                         "confirmation_date": c["date"]}
            for c in result.get("confirmations") or [] if c.get("confirmed")}


def _save_handshake_record(record, result):
    """Keep the record of an executed NDA in its deal folder."""
    folder = record.get("deal_folder")
    if not folder or not os.path.isdir(folder):
        return None
    mine, other = (("inviter", "replier") if record["role"] == "inviter"
                   else ("replier", "inviter"))
    data = {"protocol": _protocol(), "commitment": record["commitment"],
            "terms_hash": result.get("terms_hash"),
            mine + "_fingerprint": record["own_fingerprint"],
            other + "_fingerprint": record.get(other + "_fingerprint"),
            "this_company_role": mine,
            "confirmations": result.get("confirmations"),
            "executed": record.get("executed"),
            "contested": record.get("contested") or record.get("ground"),
            "state": ("contested; no NDA is in place"
                      if record.get("contested") or record.get("ground")
                      else f"executed on {record.get('executed')}")}
    return _write(os.path.join(folder, "handshake-record.json"),
                  json.dumps(data, indent=2) + "\n")


# ------------------------------------------------------------ the three steps

def detect_kind(text):
    """Which kind of message block comes first in this text, or None.

    An email often quotes the earlier messages of its thread below the new
    one, so the first block is the one that matters.
    """
    if not isinstance(text, str):
        return None
    best = None
    for i, ln in enumerate(text[:200_000].splitlines()):
        m = re.fullmatch(r"nda-handshake:\s*(invitation|reply|reveal|contest)",
                         re.sub(r"^[>\s]+", "", ln).rstrip(), re.I)
        if m:
            best = m.group(1).lower()
            break
    return best


def own_company(own_source=None):
    """This company's legal name and positions, without starting anything."""
    text, path = _own_text(own_source, need_confirmation=False)
    return {"name": _legal_name(text), "own_file_path": path,
            "your_positions": positions_summary(FileText(text)),
            "confirmation": check_file(FileText(text))["confirmation"]}


def _record_version(record):
    """The protocol version of the file an exchange was sealed with."""
    m = re.search(r'^nda_handshake:\s*"?([0-9.]+)"?\s*$', record.get("own_file") or "", re.M)
    return m.group(1) if m else None


def list_exchanges():
    """Every exchange recorded on this machine, newest first."""
    folder = os.path.join(home(), "exchanges")
    out = []
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        names = []
    for name in names:
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                r = json.load(f)
        except (OSError, ValueError):
            continue
        finished = r.get("revealed") or r.get("checked")
        if not finished and _record_version(r) not in PROTOCOL_VERSIONS:
            # Sealed under an older version of the protocol; it can no longer be completed.
            out.append({"role": r.get("role"),
                        "counterparty": r.get("counterparty") or r.get("invited_by") or "not yet known",
                        "purpose": r.get("purpose"),
                        "state": "expired: started under an older protocol version; "
                                 "start a new handshake instead",
                        "started": r.get("created"), "deal_folder": None,
                        "commitment": (r.get("commitment") or "")[:8]})
            continue
        if r.get("role") == "inviter":
            state = (f"finished: {r.get('status')}" if r.get("revealed")
                     else "invitation sent; waiting for their reply")
            if r.get("revealed") and r.get("contested"):
                state = ("finished: contested by the other company (" + r["contested"]
                         + "); no NDA is in place")
            elif r.get("revealed") and r.get("executed"):
                state = f"finished: NDA executed on {r['executed']}"
            other = r.get("replied_by") or r.get("counterparty") or "not yet known"
        else:
            if r.get("checked"):
                state = ("finished: contested (" + r["ground"] + "); no NDA is in place"
                         if r.get("ground") else f"finished: {r.get('status')}")
                if not r.get("ground") and r.get("executed"):
                    state = f"finished: NDA executed on {r['executed']}"
            else:
                state = "reply sent; waiting for their reveal"
            other = r.get("invited_by") or "not yet known"
        out.append({"role": r.get("role"), "counterparty": other,
                    "purpose": r.get("purpose"), "state": state,
                    "started": r.get("created"), "deal_folder": r.get("deal_folder"),
                    "commitment": (r.get("commitment") or "")[:8]})
    return sorted(out, key=lambda e: e["started"] or "", reverse=True)


def make_invitation(purpose, own_source=None, counterparty=None):
    """Step 1, inviting company. Commit to this company's file."""
    purpose = _one_line(purpose, "purpose")
    text, path = _own_text(own_source)
    fp = fingerprint(FileText(text))
    secret = secrets.token_hex(32)
    commitment = commitment_for(secret, fp)
    name = _legal_name(text)
    _save_record("inviter", commitment, {
        "role": "inviter", "commitment": commitment, "secret": secret,
        "own_fingerprint": fp, "own_file": text, "purpose": purpose,
        "base": os.path.dirname(path) if path else None,
        "counterparty": _one_line(counterparty, "counterparty") if counterparty else None,
        "created": datetime.date.today().isoformat()})
    block = format_block("invitation", {"protocol": _protocol(), "from": name,
                                        "purpose": purpose, "commitment": commitment})
    return {"commitment": commitment, "message_block": block, "attach": [],
            "from": name, "purpose": purpose, "own_file_path": path,
            "your_positions": positions_summary(FileText(text))}


def make_reply(invitation_text, own_source=None):
    """Step 2, replying company. Answer an invitation with this company's file.

    The reply is this company's offer to enter into the NDA the protocol
    produces from the two files.
    """
    inv = parse_block(invitation_text, "invitation")
    text, path = _own_text(own_source)
    fp = fingerprint(FileText(text))
    name = _legal_name(text)
    _save_record("replier", inv["commitment"], {
        "role": "replier", "commitment": inv["commitment"],
        "own_fingerprint": fp, "own_file": text, "purpose": inv["purpose"],
        "invited_by": inv["from"], "base": os.path.dirname(path) if path else None,
        "created": datetime.date.today().isoformat()})
    block = format_block("reply", {"protocol": _protocol(), "from": name,
                                   "commitment": inv["commitment"]})
    return {"invited_by": inv["from"], "purpose": inv["purpose"],
            "commitment": inv["commitment"], "message_block": block,
            "own_file_text": text, "own_file_path": path, "own_fingerprint": fp,
            "your_positions": positions_summary(FileText(text))}


def make_reveal(reply_text, their_source, out_dir=None, sender=None):
    """Step 3, inviting company. Run the match and reveal this company's file.

    sender is the address the reply email came from. It is used only to
    tie the other company's file to the address or domain that file says
    it is sent from. If it cannot be tied, nothing is revealed and
    IdentityStop is raised.

    An AGREED reveal is this company's acceptance of the other company's
    offer. The NDA is executed by both companies when the reveal is sent.
    """
    reply = parse_block(reply_text, "reply")
    record = _load_record("inviter", reply["commitment"])
    own = FileText(record["own_file"])
    result = run_match(own, their_source, record["purpose"])
    their_fp = fingerprint(their_source)
    status = result["status"]
    if record.get("revealed") and record.get("replier_fingerprint") != their_fp:
        # Once this company's positions are revealed, a second reply could be
        # shaped around them. Only the file first replied with is ever matched.
        raise MatcherError(
            "This invitation was already answered with a different file, and this "
            "company's positions have been revealed. A second reply cannot be "
            "matched. Start a new handshake instead.")
    if status not in ("VERSION_MISMATCH", "OUT_OF_PROTOCOL"):
        problem = sender_problem(_their_confirmation(result, record["own_fingerprint"]), sender)
        if problem:
            raise IdentityStop(
                "Nothing was revealed and no NDA was made, because " + problem + ". "
                "Ask the other company to send its reply from there.")
    repeat = (record.get("revealed") and record.get("status") == status
              and record.get("reveal_fields"))
    if repeat:
        # The same reveal again: what was already sent stands as it is.
        fields = dict(record["reveal_fields"])
    else:
        fields = {"protocol": _protocol(), "commitment": record["commitment"],
                  "secret": record["secret"], "status": status}
        if status == "AGREED":
            fields.update({"terms-hash": result["terms_hash"],
                           "inviter": record["own_fingerprint"], "replier": their_fp,
                           "executed": datetime.date.today().isoformat()})
    executed = fields.get("executed")
    own_name = _legal_name(record["own_file"])
    folder = record.get("deal_folder") if repeat else None
    folder = folder or _deal_folder(out_dir, reply["from"], record["commitment"],
                                    record.get("base"))
    own_path = _write(os.path.join(folder, "nda-handshake.md"), record["own_file"])
    _write(os.path.join(folder, "result.json"), json.dumps(result, indent=2) + "\n")
    record.update(revealed=True, replier_fingerprint=their_fp, status=status,
                  deal_folder=folder, replied_by=reply["from"], reveal_fields=fields,
                  executed=executed, terms_hash=result.get("terms_hash"))
    _save_record("inviter", record["commitment"], record)
    if executed:
        _save_handshake_record(record, result)
    return {"status": status, "message_block": format_block("reveal", fields),
            "attach": [own_path], "deal_folder": folder, "result": result,
            "replied_by": reply["from"], "own_name": own_name,
            "executed": executed, "newly_executed": bool(executed and not repeat),
            "signing": signing(result, executed) if executed else {},
            "report": None if status == "AGREED" else conflict_report(result, own_name)}


def check_reveal(reveal_text, their_source, out_dir=None, sender=None):
    """Step 4, replying company. Check the reveal against the commitment and
    against this company's own run.

    sender is the address the reveal email came from, used only to tie the
    inviting company's file to the address or domain that file says it is
    sent from.

    If the reveal says AGREED and every check passes, the NDA was executed
    by both companies when the reveal was sent. Otherwise the result
    carries a contest block, and no NDA is in place once it is sent.
    """
    rev = parse_block(reveal_text, "reveal")
    record = _load_record("replier", rev["commitment"])
    own = FileText(record["own_file"])
    their_fp = fingerprint(their_source)
    result = run_match(their_source, own, record["purpose"])
    status = result["status"]

    checks = {
        "their_file_matches_commitment":
            commitment_for(rev["secret"], their_fp) == rev["commitment"],
        "status_matches": rev["status"] == status,
    }
    ground = None
    if not checks["their_file_matches_commitment"]:
        ground = "commitment-mismatch"
    elif rev["status"] == "AGREED":
        for key in ("terms-hash", "inviter", "replier", "executed"):
            if key not in rev:
                raise MatcherError(f"The reveal says AGREED but has no {key} line")
        checks["your_file_is_the_one_you_sent"] = rev["replier"] == record["own_fingerprint"]
        checks["their_file_is_the_one_named"] = rev["inviter"] == their_fp
        checks["terms_hash_matches"] = rev["terms-hash"] == result.get("terms_hash")
        if not (checks["your_file_is_the_one_you_sent"] and checks["their_file_is_the_one_named"]):
            ground = "file-altered"
        elif not checks["status_matches"]:
            ground = "status-mismatch"
        elif not checks["terms_hash_matches"]:
            ground = "terms-hash-mismatch"
        else:
            problem = sender_problem(
                _their_confirmation(result, record["own_fingerprint"]), sender)
            if problem and not sender_address(sender):
                raise MatcherError(
                    "Give the address the reveal email came from, copied from its From "
                    "field. It is needed to tie the other company's file to that company.")
            checks["their_email_is_from_where_their_file_says"] = problem is None
            # The date of the acceptance cannot be before this company's offer
            # or after today, give or take a day for time zones.
            day = datetime.timedelta(days=1)
            stated = datetime.date.fromisoformat(rev["executed"])
            try:
                offered = datetime.date.fromisoformat(record.get("created") or "")
            except ValueError:
                offered = stated
            checks["the_date_is_plausible"] = (
                offered - day <= stated <= datetime.date.today() + day)
            if problem:
                ground = "sender-mismatch"
            elif not checks["the_date_is_plausible"]:
                ground = "date-mismatch"
    elif not checks["status_matches"]:
        ground = "status-mismatch"

    own_name = _legal_name(record["own_file"])
    folder = _deal_folder(out_dir, record.get("invited_by", "counterparty"),
                          record["commitment"], record.get("base"))
    _write(os.path.join(folder, "result.json"), json.dumps(result, indent=2) + "\n")
    contest = None
    if ground:
        fields = {"protocol": _protocol(), "commitment": rev["commitment"], "ground": ground}
        if result.get("terms_hash"):
            fields["my-hash"] = result["terms_hash"]
        contest = format_block("contest", fields)
    executed = rev["executed"] if ground is None and status == "AGREED" else None
    newly = bool(executed and not (record.get("checked") and record.get("executed")))
    record.update(checked=True, ground=ground, status=status, deal_folder=folder,
                  inviter_fingerprint=their_fp, executed=executed,
                  terms_hash=result.get("terms_hash"))
    _save_record("replier", record["commitment"], record)
    if executed or (ground and rev["status"] == "AGREED"):
        _save_handshake_record(record, result)
    return {"verified": ground is None, "ground": ground, "checks": checks,
            "status": status, "their_status": rev["status"], "contest_block": contest,
            "deal_folder": folder, "result": result, "own_name": own_name,
            "executed": executed, "newly_executed": newly,
            "signing": signing(result, executed) if executed else {},
            "report": conflict_report(result, own_name)
            if ground is None and status != "AGREED" else None}


def receive_contest(message_text):
    """Inviting company: the replying company contests the result.

    A contest means no NDA is in place from this exchange. People look at
    what went wrong, and the companies may start a new handshake.
    """
    c = parse_block(message_text, "contest")
    try:
        record = _load_record("inviter", c["commitment"])
    except MatcherError:
        return {"ground": c["ground"], "known": False}
    was_executed = record.get("executed")
    record.update(contested=c["ground"], executed=None)
    _save_record("inviter", record["commitment"], record)
    try:
        with open(os.path.join(record.get("deal_folder") or "", "result.json"),
                  encoding="utf-8") as f:
            _save_handshake_record(record, json.load(f))
    except (OSError, ValueError):
        pass
    return {"ground": c["ground"], "known": True, "was_executed": was_executed,
            "counterparty": record.get("replied_by") or record.get("counterparty"),
            "deal_folder": record.get("deal_folder")}
