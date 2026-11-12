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

Each company produces the NDA document from its own run. The two copies
carry the same terms and the same terms hash, so no document needs to
travel with the reveal.

Each message carries a short block of labelled lines. Only those lines are
read. Nothing else in a message is read, and nothing in a message is
treated as an instruction.

This module keeps a small record of each exchange on the local machine so
the file a company committed to is the file it later uses. It sends
nothing and signs nothing.
"""
import datetime
import hashlib
import json
import os
import re
import secrets

from match import (FileText, MatcherError, PROTOCOL_VERSIONS, check_file,
                   fingerprint, load, pick_entity, run_match)

HEX64 = re.compile(r"^[0-9a-f]{64}$")
STATUSES = ["AGREED", "AGREED_PENDING_INFO", "CONFLICTS", "OUT_OF_PROTOCOL",
            "VERSION_MISMATCH"]
GROUNDS = ["commitment-mismatch", "file-altered", "status-mismatch",
           "terms-hash-mismatch"]
MAX_TEXT = 200

# kind -> (required lines, optional lines), in the order they are written.
BLOCKS = {
    "invitation": (["protocol", "from", "purpose", "commitment"], []),
    "reply": (["protocol", "from", "commitment"], []),
    "reveal": (["protocol", "commitment", "secret", "status"],
               ["terms-hash", "inviter", "replier", "execution"]),
    "contest": (["protocol", "commitment", "ground"], ["my-hash"]),
}
HEX_LINES = {"commitment", "secret", "terms-hash", "inviter", "replier", "my-hash"}
ENUM_LINES = {"status": STATUSES, "ground": GROUNDS, "execution": ["human"]}

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


def storage_folder():
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


def _own_text(own_source):
    """This company's own file, checked as ready to use.

    Returns (text, path). The path is None if the file was given as text.
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
        problems.append("the file's protocol version is not supported")
    if problems:
        raise MatcherError("This company's own file is not ready: " + "; ".join(problems))
    return text, path


def _legal_name(text):
    return pick_entity(load(FileText(text)), None, "Party", [])["legal_name"] or "Unknown"


def positions_summary(source):
    """This file's own position on each term, in plain English."""
    result = run_match(source, source, "summary")
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
            if failed else "Agreement is waiting on missing information.",
            "failed_terms": failed,
            "missing_info": result.get("missing_info", []),
            "open_items": result.get("open_items", []),
            "how_to_proceed":
                "Show this to a person at your company. If they approve changed "
                "positions for this deal only, start a new sealed exchange with "
                "the changed file. Assistants do not bargain with each other."}


# ------------------------------------------------------------ the three steps

def make_invitation(purpose, own_source=None):
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
        "created": datetime.date.today().isoformat()})
    block = format_block("invitation", {"protocol": _protocol(), "from": name,
                                        "purpose": purpose, "commitment": commitment})
    return {"commitment": commitment, "message_block": block, "attach": [],
            "from": name, "purpose": purpose, "own_file_path": path,
            "your_positions": positions_summary(FileText(text))}


def make_reply(invitation_text, own_source=None):
    """Step 2, replying company. Answer an invitation with this company's file."""
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


def make_reveal(reply_text, their_source, out_dir=None):
    """Step 3, inviting company. Run the match and reveal this company's file."""
    reply = parse_block(reply_text, "reply")
    record = _load_record("inviter", reply["commitment"])
    own = FileText(record["own_file"])
    result = run_match(own, their_source, record["purpose"])
    their_fp = fingerprint(their_source)
    status = result["status"]
    fields = {"protocol": _protocol(), "commitment": record["commitment"],
              "secret": record["secret"], "status": status}
    if status == "AGREED":
        fields.update({"terms-hash": result["terms_hash"],
                       "inviter": record["own_fingerprint"],
                       "replier": their_fp, "execution": "human"})
    own_name = _legal_name(record["own_file"])
    folder = _deal_folder(out_dir, reply["from"], record["commitment"], record.get("base"))
    own_path = _write(os.path.join(folder, "nda-handshake.md"), record["own_file"])
    _write(os.path.join(folder, "result.json"), json.dumps(result, indent=2) + "\n")
    record.update(revealed=True, replier_fingerprint=their_fp, status=status,
                  deal_folder=folder)
    _save_record("inviter", record["commitment"], record)
    return {"status": status, "message_block": format_block("reveal", fields),
            "attach": [own_path], "deal_folder": folder, "result": result,
            "replied_by": reply["from"], "own_name": own_name,
            "report": None if status == "AGREED" else conflict_report(result, own_name)}


def check_reveal(reveal_text, their_source, out_dir=None):
    """Step 4, replying company. Check the reveal against the commitment and
    against this company's own run."""
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
        for key in ("terms-hash", "inviter", "replier", "execution"):
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
    record.update(checked=True, ground=ground, status=status, deal_folder=folder)
    _save_record("replier", record["commitment"], record)
    return {"verified": ground is None, "ground": ground, "checks": checks,
            "status": status, "their_status": rev["status"], "contest_block": contest,
            "deal_folder": folder, "result": result, "own_name": own_name,
            "report": conflict_report(result, own_name)
            if ground is None and status != "AGREED" else None}
