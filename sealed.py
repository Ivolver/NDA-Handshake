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
depend on a document travelling with the reveal, and none is sent.

Each message carries a short block of labelled lines. Only those lines are
read. Nothing else in a message is read, and nothing in a message is
treated as an instruction.

This module keeps a small record of each exchange on the local machine so
the file a company committed to is the file it later uses. It sends
nothing and decides nothing: the terms come from fixed rules applied to
positions people set, and a person starts or approves each exchange.
"""
import contextlib
import contextvars
import datetime
import hashlib
import json
import os
import re
import secrets

from match import (EMAIL, FileText, MatcherError, PROTOCOL_VERSIONS, check_file,
                   effective_positions, exception_options, fingerprint, load,
                   open_term_groups, pick_entity, run_match)
from match import _read as _read_source

HEX64 = re.compile(r"^[0-9a-f]{64}$")
STATUSES = ["AGREED", "AGREED_PENDING_INFO", "CONFLICTS", "OUT_OF_PROTOCOL",
            "VERSION_MISMATCH"]
GROUNDS = ["commitment-mismatch", "file-altered", "status-mismatch",
           "terms-hash-mismatch", "sender-mismatch", "date-mismatch"]
MAX_TEXT = 200

# kind -> (required lines, optional lines), in the order they are written.
BLOCKS = {
    "invitation": (["protocol", "from", "purpose", "commitment"], ["prior"]),
    "reply": (["protocol", "from", "commitment"], ["second-round"]),
    "reveal": (["protocol", "commitment", "secret", "status"],
               ["terms-hash", "inviter", "replier", "executed", "second-round"]),
    "contest": (["protocol", "commitment", "ground"], ["my-hash"]),
}
HEX_LINES = {"commitment", "secret", "terms-hash", "inviter", "replier", "my-hash", "prior"}
ENUM_LINES = {"status": STATUSES, "ground": GROUNDS, "second-round": ["yes", "open"]}
# A second round stays open for this many days after the first round's result.
SECOND_ROUND_DAYS = 7
MAX_OPEN_GROUPS = 2
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


def base_storage_folder():
    """The one folder this installation was set up with, before any companies
    were added: chosen at install, or with the setup tool."""
    chosen = installer_storage_folder()
    if chosen:
        os.makedirs(chosen, exist_ok=True)
        return chosen
    folder = read_settings().get("storage_folder")
    return folder if isinstance(folder, str) and folder else None


# ------------------------------------------------------------------ companies
#
# One installation can act for more than one company. Each company has its
# own folder, holding its own nda-handshake.md, confirmation and deals. The
# list lives in companies.json beside the settings. Until a second company is
# added there is no list, and everything works from the one folder the
# installation was set up with, exactly as before.

_ACTING = contextvars.ContextVar("nda_handshake_acting_folder", default=None)


def read_companies():
    """{"active": name or None, "companies": {name: folder}}."""
    try:
        with open(os.path.join(home(), "companies.json"), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    companies = data.get("companies") if isinstance(data, dict) else None
    companies = {str(k): v for k, v in (companies or {}).items()
                 if isinstance(v, str) and v}
    active = data.get("active") if isinstance(data, dict) else None
    return {"active": active if active in companies else None, "companies": companies}


def _save_companies(data):
    _write_private(os.path.join(home(), "companies.json"), data)


def storage_folder():
    """The folder of the company this call is acting for.

    In order: a company chosen for this one call, the active company if
    companies have been added, then the folder the installation was set up
    with.
    """
    acting = _ACTING.get()
    if acting:
        return acting
    listed = read_companies()
    if listed["active"]:
        folder = listed["companies"][listed["active"]]
        os.makedirs(folder, exist_ok=True)
        return folder
    return base_storage_folder()


@contextlib.contextmanager
def acting_as(folder):
    """Act for the company kept in this folder, for the calls made inside."""
    token = _ACTING.set(folder)
    try:
        yield folder
    finally:
        _ACTING.reset(token)


def _company_facts(folder):
    """What a company's folder says about it, without failing on a missing file."""
    path = os.path.join(folder, "nda-handshake.md")
    facts = {"folder": folder, "file": os.path.isfile(path), "legal_name": None,
             "known_as": None, "confirmed": False, "sent_from": None, "readable": True}
    if not facts["file"]:
        return facts
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        # The file is there but this computer will not let it be opened.
        facts["readable"] = False
        return facts
    try:
        data = load(FileText(text))
        facts["legal_name"] = _legal_name(text)
        company = data.get("company")
        if isinstance(company, dict) and isinstance(company.get("name"), str):
            facts["known_as"] = company["name"].strip() or None
        report = check_file(FileText(text))["confirmation"]
        facts["confirmed"], facts["sent_from"] = bool(report["ready"]), report["sent_from"]
    except (MatcherError, KeyError, TypeError, ValueError):
        pass
    return facts


def list_companies():
    """Every company this installation can act for, with which one is active.

    Before any company has been added, this is the one company the
    installation was set up with, if there is one.
    """
    listed = read_companies()
    if not listed["companies"]:
        base = base_storage_folder()
        if not base:
            return []
        facts = _company_facts(base)
        return [dict(facts, name=facts["known_as"] or facts["legal_name"]
                     or os.path.basename(base.rstrip(os.sep)) or "this company",
                     active=True, listed=False)]
    return [dict(_company_facts(folder), name=name, active=name == listed["active"],
                 listed=True)
            for name, folder in sorted(listed["companies"].items(), key=lambda kv: kv[0].lower())]


def find_company(name):
    """The one company a name refers to: its name here, its legal name, or
    the start of either. Case does not matter. The name a company is listed
    under comes first, so a listed name always finds its own company even
    when another company trades under the same word."""
    wanted = " ".join((name or "").split()).lower()
    if not wanted:
        raise MatcherError("Say which company.")
    companies = list_companies()

    def names(c):
        return [n.lower() for n in (c["name"], c["legal_name"], c["known_as"]) if n]
    own = [c for c in companies if c["name"].lower() == wanted]
    exact = own or [c for c in companies if wanted in names(c)]
    close = exact or [c for c in companies if any(n.startswith(wanted) for n in names(c))]
    if len(close) == 1:
        return close[0]
    known = ", ".join(c["name"] for c in companies) or "none yet"
    if not close:
        raise MatcherError(f"No company called \"{name}\" is set up here. Set up: {known}.")
    raise MatcherError(f"\"{name}\" could mean more than one company. Set up: {known}.")


def add_company(name, folder):
    """Add a company with its own folder and make it the active one.

    The first time a company is added, the company the installation was
    already set up with is put on the list too, so it is not lost.
    """
    name = " ".join((name or "").split())
    if not name or len(name) > 80:
        raise MatcherError("Give the company a short name to call it by.")
    if not folder or "://" in folder:
        raise MatcherError("Give a local folder for this company's files.")
    folder = os.path.abspath(os.path.expanduser(folder))
    listed = read_companies()
    companies = dict(listed["companies"])
    if not companies:
        base = base_storage_folder()
        if base and os.path.abspath(base) != folder:
            first = list_companies()[0]
            companies[first["name"]] = os.path.abspath(base)
    for other, where in companies.items():
        if other.lower() == name.lower():
            raise MatcherError(f"A company called \"{other}\" is already set up here.")
        if os.path.abspath(where) == folder:
            raise MatcherError(f"That folder already belongs to \"{other}\". Each company "
                               "needs a folder of its own.")
    os.makedirs(folder, exist_ok=True)
    companies[name] = folder
    _save_companies({"active": name, "companies": companies})
    return find_company(name)


def switch_company(name):
    """Make a company the active one."""
    company = find_company(name)
    listed = read_companies()
    companies = dict(listed["companies"])
    if not company["listed"]:
        companies[company["name"]] = os.path.abspath(company["folder"])
    _save_companies({"active": company["name"], "companies": companies})
    return find_company(company["name"])


def remove_company(name):
    """Take a company off the list. Its folder and files are left alone."""
    company = find_company(name)
    listed = read_companies()
    if not company["listed"]:
        raise MatcherError("That is the only company set up here, so there is nothing "
                           "to take off the list.")
    companies = {k: v for k, v in listed["companies"].items() if k != company["name"]}
    active = listed["active"] if listed["active"] in companies else None
    if active is None and companies:
        active = sorted(companies, key=str.lower)[0]
    _save_companies({"active": active, "companies": companies})
    return company


def company_positions(folder):
    """A company's nine positions in plain words, for showing to a person."""
    path = os.path.join(folder, "nda-handshake.md")
    if not os.path.isfile(path):
        raise MatcherError("This company has no nda-handshake.md yet.")
    with open(path, encoding="utf-8") as f:
        nda = effective_positions(load(FileText(f.read())))
    from match import LIST_TERMS, RANGES, TOGGLES
    order = [n for n, _ in LIST_TERMS] + list(RANGES) + list(TOGGLES)
    return [{"term": name, "label": TERM_LABELS.get(name, name),
             "position": _describe(name, nda.get(name))}
            for name in TERM_LABELS if name in order]


def acting_company(message_text=None):
    """Which company a call acts for, and the address its emails must come from.

    An email that belongs to an exchange already under way acts for the
    company that started or answered it, whichever company is active now.
    """
    text = None
    if message_text:
        try:
            kind = detect_kind(message_text)
            block = parse_block(message_text, kind)
            role = {"reply": "inviter", "reveal": "replier", "contest": "inviter"}.get(kind)
            if kind == "invitation" and block.get("prior"):
                role, block = "replier", {"commitment": block["prior"]}
            if role:
                text = _load_record(role, block["commitment"])["own_file"]
        except (MatcherError, KeyError):
            text = None
    if text is None:
        path = own_file_path()
        if not (path and os.path.isfile(path)):
            return None
        with open(path, encoding="utf-8") as f:
            text = f.read()
    try:
        report = check_file(FileText(text))["confirmation"]
        return {"company": _legal_name(text), "send_from": report["sent_from"]}
    except (MatcherError, KeyError):
        return None


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


def email_html(body):
    """An email body as HTML, for mail tools that can send it.

    People see flowing paragraphs and a link shown by its plain address.
    The block for the assistants is kept exactly, in fixed-width type. A
    plain web address in running text is often rewritten by mail services
    into a long tracking link; a link with its own text is shown as that
    text.
    """
    import html as _html

    def linked(text):
        out, pos = [], 0
        for m in re.finditer(r"https://[^\s<>\"]+[^\s<>\".,;:!?)]", text):
            out.append(_html.escape(text[pos:m.start()]))
            url = m.group(0)
            out.append(f'<a href="{_html.escape(url, quote=True)}">'
                       f'{_html.escape(url[len("https://"):])}</a>')
            pos = m.end()
        return "".join(out) + _html.escape(text[pos:])

    human, found, block = body.partition(DIVIDER)
    parts = []
    for para in re.split(r"\n\s*\n", human.strip("\n")):
        lines = para.split("\n")
        if any(ln.startswith("  ") for ln in lines):
            # Indented lines are a short list or a set of terms: keep each on its own line.
            if not lines[0].startswith("  "):
                parts.append('<p style="margin:0 0 6px">' + linked(lines[0].strip()) + "</p>")
                lines = lines[1:]
            items, current = [], None
            for ln in lines:
                starts = ln.startswith("  ") and not ln.startswith("    ")
                if starts or current is None:
                    current = ln.strip()
                    items.append(current)
                else:
                    items[-1] += " " + ln.strip()
            parts.append('<p style="margin:0 0 14px 18px">'
                         + "<br>".join(linked(i) for i in items) + "</p>")
        else:
            parts.append('<p style="margin:0 0 14px">'
                         + linked(" ".join(ln.strip() for ln in lines)) + "</p>")
    if found:
        parts.append('<pre style="font-family:Menlo,Consolas,monospace;font-size:12px;'
                     'color:#555;margin:22px 0 0">' + _html.escape(DIVIDER + block) + "</pre>")
    return ('<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;'
            'line-height:1.5;color:#222">' + "".join(parts) + "</div>")


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


def second_invitation_email(own_name, block):
    return (f"\U0001F91D NDA Handshake, second round: {own_name}",
            _email([
                "Our first handshake came close but did not meet on every term, so this",
                "opens the second and final round.",
                "",
                "It works the same way. Our second-round positions are sealed in the code",
                "below. Your assistant replies with yours, changed or not, and we then",
                "open ours. A person at each company decides, privately, whether to allow",
                "an exception for this one NDA. Neither side sees the other's decision",
                "first. If the positions now meet, the NDA is in place right then.",
                "",
                "Please ask your assistant to handle this email.",
            ], block))


def reply_email(own_name, block):
    return _email([
        f"Happy to shake on it. {own_name}'s NDA positions are attached.",
        "",
        "Your move: once your assistant opens your sealed positions, both sides",
        "will see the same result. If our positions meet, the NDA is in place when",
        "your assistant sends that result.",
    ], block)


def reveal_email(result, block, second_round_open=False):
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
                  "business day. Your assistant produces your copy of the executed NDA from",
                  "its own run, identical to ours, and saves it for you."]
    elif status == "CONFLICTS":
        failed = [TERM_LABELS.get(e["term"], e["term"]).replace(" (years)", "")
                  for e in (result.get("summary") or {}).get("terms", [])
                  if e.get("outcome") == "CONFLICT"]
        lines = ["No handshake this time. Our positions and yours did not meet on:", ""]
        lines += [f"  {label}" for label in failed]
        lines += ["",
                  "Our positions are attached, as promised, so your side can see the same",
                  "result."]
        if second_round_open:
            lines += ["",
                      "A second round is open for one week. In it, a person at each company",
                      "can approve an exception on these terms for this NDA only, and both",
                      "sides commit again under seal. Your assistant can explain your",
                      "options. If we go ahead, you will get one more email from us."]
        else:
            lines += ["If someone on your team would like to talk it through, just reply.",
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
    out = {}
    for c in result.get("confirmations") or []:
        if not c.get("confirmed"):
            continue
        out[c["party"]] = {"date": executed, "confirmed_by": c["confirmed_by"],
                           "confirmation_date": c["date"]}
        if c.get("exception"):
            out[c["party"]].update(exception_by=c["exception"]["approved_by"],
                                   exception_date=c["exception"]["date"])
    return out


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


# ------------------------------------------------------------ the second round
#
# When a first round ends in CONFLICTS on one or two terms, and both sides'
# software says it can, one second round is open for a week. Each company's
# person may approve a one-deal exception: a wider position on a failed
# term, for this NDA only. The assistants never bargain. Each asks only its
# own person, both sides commit again under seal, and the same rule decides.

def second_round_allowed(own_text):
    """False if the company's file switches second rounds off."""
    nda = load(FileText(own_text)).get("nda")
    return not (isinstance(nda, dict) and nda.get("second_round") is False)


def second_round_terms(result):
    """The terms a second round would be open for, or [] if it is not eligible."""
    if result.get("status") != "CONFLICTS":
        return []
    names = [e["term"] for e in (result.get("summary") or {}).get("terms", [])
             if e.get("outcome") == "CONFLICT"]
    if not names or "form" in names or open_term_groups(names) > MAX_OPEN_GROUPS:
        return []
    return names


def _source_text(source):
    return _read_source(source)[0].decode("utf-8")


def _opened(result, their_source):
    until = datetime.date.today() + datetime.timedelta(days=SECOND_ROUND_DAYS)
    return {"state": "open", "terms": second_round_terms(result),
            "their_file": _source_text(their_source), "until": until.isoformat()}


def _second(record):
    """For a second-round record: what run_match needs. None in a first round."""
    if not record.get("prior"):
        return None
    return {"prior": record["prior"], "terms": record["open_terms"]}


def _same_but_exception(their_source, round_one_text):
    """True if a second-round file is the first-round file plus, at most, an exception."""
    now, before = load(their_source), load(FileText(round_one_text))
    now.pop("exception", None)
    return now == before and "exception" not in before


def _describe(name, position):
    scrap = []
    from match import LIST_TERMS, RANGES, describe_choice, describe_range, ranked, read_range
    allowed = dict(LIST_TERMS).get(name)
    if allowed is not None:
        return describe_choice(ranked(position, allowed, name, "", scrap))
    if name in RANGES:
        return describe_range(read_range(position, RANGES[name], name, "", scrap))
    return (str(position or "accept")).capitalize()


def second_round_view(record):
    """What a company's person needs to decide on a second round.

    For each open term: this company's position, the other company's, and
    the wider positions this company could take for this one NDA.
    """
    info = record.get("second_round") or {}
    mine = effective_positions(load(FileText(record["own_file"])))
    theirs = effective_positions(load(FileText(info["their_file"])))
    terms = []
    for name in info.get("terms", []):
        options = exception_options(name, mine.get(name), theirs.get(name))
        terms.append({
            "term": name, "label": TERM_LABELS.get(name, name).replace(" (years)", ""),
            "your_position": _describe(name, mine.get(name)),
            "their_position": _describe(name, theirs.get(name)),
            "accept_theirs": options["accept_theirs"],
            "accept_theirs_means": options["accept_theirs"] is not None
            and _describe(name, options["accept_theirs"]),
            "neutral": options["neutral"], "neutral_value": options["neutral_value"],
            "neutral_means": options["neutral"] is not None
            and _describe(name, options["neutral"])})
    other = (record.get("replied_by") if record["role"] == "inviter"
             else record.get("invited_by")) or record.get("counterparty") or "the other company"
    return {"commitment": record["commitment"], "role": record["role"],
            "counterparty": other, "purpose": record["purpose"],
            "state": info.get("state"), "until": info.get("until"), "terms": terms,
            "invitation_received": bool(info.get("invitation"))}


def open_second_rounds():
    """Every first-round record on this machine with a second round still open."""
    out, folder = [], os.path.join(home(), "exchanges")
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return out
    today = datetime.date.today().isoformat()
    for name in names:
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                record = json.load(f)
        except (OSError, ValueError):
            continue
        info = record.get("second_round") if isinstance(record, dict) else None
        if info and info.get("state") == "open" and (info.get("until") or "") >= today:
            out.append(record)
    return out


def find_second_round(commitment=None):
    """The one open second round meant, by the start of its commitment if given."""
    found = [r for r in open_second_rounds()
             if not commitment or r["commitment"].startswith(commitment.lower())]
    try:
        me = own_company()["name"]
    except (MatcherError, OSError):
        me = None
    if me and len(found) > 1:
        # One computer can hold more than one company's records: prefer the
        # company being acted for now.
        mine = [r for r in found if _legal_name(r["own_file"]) == me]
        found = mine or found
    if not found:
        raise MatcherError("No second round is open here. One opens only when a first "
                           "round ended without agreement on one or two terms, both "
                           "companies allow it, and less than a week has passed.")
    if len(found) > 1:
        raise MatcherError("More than one second round is open. Say which by giving the "
                           "commitment: " + ", ".join(r["commitment"][:8] for r in found))
    return found[0]


def exception_terms(record, choice, only=None):
    """The wider positions a choice means on each open term.

    choice is "accept_theirs" or "neutral". only limits it to some of the
    open terms; governing law and venue always move together.
    """
    view = second_round_view(record)
    wanted = set(only or [t["term"] for t in view["terms"]])
    if wanted & {"governing_law", "venue"}:
        wanted |= {"governing_law", "venue"}
    out = {}
    for t in view["terms"]:
        if t["term"] not in wanted:
            continue
        position = t[choice]
        if position is None:
            raise MatcherError(
                f"There is no {'neutral option' if choice == 'neutral' else 'wider position'} "
                f"for {t['label']}. Choose again for that term.")
        out[t["term"]] = position
    if not out:
        raise MatcherError("That choice covers none of the open terms.")
    return out


def decline_second_round(record):
    record["second_round"]["state"] = "declined"
    _save_record(record["role"], record["commitment"], record)


def note_second_invitation(invitation_text):
    """Replying company: a second-round invitation has arrived. Keep it and
    return what the person needs to decide."""
    inv = parse_block(invitation_text, "invitation")
    if not inv.get("prior"):
        raise MatcherError("This invitation does not open a second round.")
    try:
        record = _load_record("replier", inv["prior"])
    except MatcherError:
        raise MatcherError("This invitation opens a second round of a handshake this "
                           "computer has no record of, so it cannot be answered here.")
    info = record.get("second_round") or {}
    if info.get("state") != "open":
        raise MatcherError("No second round is open for that handshake"
                           + (": it was already answered." if info.get("state") == "replied"
                              else "."))
    if (info.get("until") or "") < datetime.date.today().isoformat():
        raise MatcherError("The second round for that handshake has closed.")
    info["invitation"] = format_block("invitation", inv)
    _save_record("replier", record["commitment"], record)
    return second_round_view(record)


def run_second_round(record, deal_text):
    """Send this company's second-round file under seal (inviter) or in reply
    (replier). deal_text is its first-round file, with an exception added if
    a person approved one."""
    info, role = record["second_round"], record["role"]
    if deal_text != record["own_file"] and not _same_but_exception(
            FileText(deal_text), record["own_file"]):
        raise MatcherError("A second-round file may differ from the first only by an exception.")
    text, _ = _own_text(FileText(deal_text))
    fp, name = fingerprint(FileText(text)), _legal_name(text)
    shared = {"own_fingerprint": fp, "own_file": text, "purpose": record["purpose"],
              "base": record.get("base"), "created": datetime.date.today().isoformat(),
              "prior": record["commitment"], "open_terms": info["terms"],
              "their_round_one_file": info["their_file"]}
    if role == "inviter":
        secret = secrets.token_hex(32)
        commitment = commitment_for(secret, fp)
        _save_record("inviter", commitment, dict(
            shared, role="inviter", commitment=commitment, secret=secret,
            counterparty=record.get("replied_by") or record.get("counterparty")))
        block = format_block("invitation", {
            "protocol": _protocol(), "from": name, "purpose": record["purpose"],
            "commitment": commitment, "prior": record["commitment"]})
        info.update(state="invited", commitment=commitment)
        out = {"kind": "invitation", "message_block": block, "attach_text": None,
               "attach": []}
    else:
        if not info.get("invitation"):
            raise MatcherError("Their second-round email has not arrived yet. When it "
                               "does, pass it to handshake and I will pick this up.")
        inv = parse_block(info["invitation"], "invitation")
        _save_record("replier", inv["commitment"], dict(
            shared, role="replier", commitment=inv["commitment"], invited_by=inv["from"]))
        block = format_block("reply", {"protocol": _protocol(), "from": name,
                                       "commitment": inv["commitment"]})
        info.update(state="replied", commitment=inv["commitment"])
        folder = _deal_folder(None, inv["from"], inv["commitment"], record.get("base"))
        out = {"kind": "reply", "message_block": block, "attach_text": text,
               "attach": [_write(os.path.join(folder, "nda-handshake.md"), text)]}
    _save_record(role, record["commitment"], record)
    return dict(out, own_name=name, counterparty=second_round_view(record)["counterparty"],
                purpose=record["purpose"], used_exception=deal_text != record["own_file"])


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
                # This software prepares the result email; it cannot see it leave.
                state = (f"finished: agreed on {r['executed']}; the NDA is in place "
                         "once the result email has been sent")
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
    if inv.get("prior"):
        raise MatcherError("This invitation opens a second round. Use the second_round "
                           "tool to answer it.")
    text, path = _own_text(own_source)
    fp = fingerprint(FileText(text))
    name = _legal_name(text)
    _save_record("replier", inv["commitment"], {
        "role": "replier", "commitment": inv["commitment"],
        "own_fingerprint": fp, "own_file": text, "purpose": inv["purpose"],
        "invited_by": inv["from"], "base": os.path.dirname(path) if path else None,
        "created": datetime.date.today().isoformat()})
    block = format_block("reply", {
        "protocol": _protocol(), "from": name, "commitment": inv["commitment"],
        "second-round": "yes" if second_round_allowed(text) else None})
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
    second = _second(record)
    if second and not _same_but_exception(their_source, record["their_round_one_file"]):
        raise IdentityStop(
            "Nothing was revealed and no NDA was made, because the file they sent for "
            "the second round is not their first-round file with, at most, an "
            "exception added. In a second round nothing else may change.")
    result = run_match(own, their_source, record["purpose"], second_round=second)
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
        elif (not second and reply.get("second-round") == "yes"
              and second_round_allowed(record["own_file"]) and second_round_terms(result)):
            fields["second-round"] = "open"
            record["second_round"] = _opened(result, their_source)
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
            "round": 2 if second else 1,
            "second_round": (second_round_view(record)
                             if fields.get("second-round") == "open" else None),
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
    second = _second(record)
    result = run_match(their_source, own, record["purpose"], second_round=second)
    status = result["status"]

    checks = {
        "their_file_matches_commitment":
            commitment_for(rev["secret"], their_fp) == rev["commitment"],
        "status_matches": rev["status"] == status,
    }
    ground = None
    if not checks["their_file_matches_commitment"]:
        ground = "commitment-mismatch"
    elif second and not _same_but_exception(their_source, record["their_round_one_file"]):
        # In a second round a file may differ from the first round's only by an exception.
        checks["their_file_changed_only_by_an_exception"] = False
        ground = "file-altered"
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
    opened = (ground is None and not second and rev.get("second-round") == "open"
              and status == "CONFLICTS" and second_round_allowed(record["own_file"])
              and second_round_terms(result))
    if opened and not (record.get("second_round") or {}).get("state") in ("replied", "declined"):
        record["second_round"] = _opened(result, their_source)
    _save_record("replier", record["commitment"], record)
    if executed or (ground and rev["status"] == "AGREED"):
        _save_handshake_record(record, result)
    return {"verified": ground is None, "ground": ground, "checks": checks,
            "status": status, "their_status": rev["status"], "contest_block": contest,
            "deal_folder": folder, "result": result, "own_name": own_name,
            "executed": executed, "newly_executed": newly,
            "signing": signing(result, executed) if executed else {},
            "round": 2 if second else 1,
            "second_round": second_round_view(record) if opened else None,
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
