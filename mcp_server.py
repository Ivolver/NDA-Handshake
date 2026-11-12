#!/usr/bin/env python3
"""Local MCP server for NDA Handshake.

Runs over stdio. Exposes five tools so an AI assistant can draft, check or
fingerprint an nda-handshake.md file, match two of them, and turn an AGREED
result into a signable Word document.

Every tool takes a file either as a local path or as its text, so an
assistant can work from an email attachment it has already read without
saving anything to disk.

Safety rules:
- Nothing is fetched from the network. Any path containing "://" is refused.
- The tools return only the structured result and output paths. The body
  text of an nda-handshake.md is never read or returned; only the typed
  YAML fields at the top.
- Nothing here signs, sends, or publishes anything. The cover page is an
  unsigned draft for human review.
"""
import json
import os
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

import make_cover_page
import make_file
from match import (
    FileText,
    MatcherError,
    check_file as run_check_file,
    fingerprint as compute_fingerprint,
    render,
    run_match,
)

mcp = MCPServer("nda-handshake")

READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)

WRITES_LOCAL_FILES = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


def _local_file(path: str) -> str:
    """Return an absolute path to a local file. Refuse URLs and missing files."""
    if "://" in path:
        raise ToolError("Only local file paths are allowed; URLs are refused.")
    p = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(p):
        raise ToolError(f"Not a file: {p}")
    return p


def _local_dir(path: str) -> str:
    """Return an absolute path to a local directory, creating it if needed."""
    if "://" in path:
        raise ToolError("Only local directory paths are allowed; URLs are refused.")
    p = os.path.abspath(os.path.expanduser(path))
    os.makedirs(p, exist_ok=True)
    if not os.path.isdir(p):
        raise ToolError(f"Not a directory: {p}")
    return p


def _source(path: str, content: str, what: str):
    """One nda-handshake.md, given as a local path or as its text. Exactly one is required."""
    if bool(path) == bool(content):
        raise ToolError(f"Give {what} either as a local path or as its text, not both and not neither.")
    return FileText(content) if content else _local_file(path)


@mcp.tool(annotations=WRITES_LOCAL_FILES)
def draft_file(legal_name: str, entity_type: str, formed_in: str, address: str,
               signatory_name: str, signatory_title: str, notices_email: str,
               use_default_positions: bool = True,
               positions: dict[str, Any] | None = None,
               custom_terms_required: bool = False,
               company_name: str = "", website: str = "",
               out_path: str = "") -> dict[str, Any]:
    """Draft a company's own nda-handshake.md from its facts and NDA positions.

    This is the onboarding step for a company that has no file yet. Gather
    the seven party facts from the user. For positions, either set
    use_default_positions (the protocol's balanced defaults for every term
    not stated) or pass positions in the same shape as the nda block of an
    nda-handshake.md, for example
    {"confidentiality_years": {"prefer": 2, "min": 1, "max": 5},
     "governing_law": {"prefer": "Delaware", "accept": ["Delaware", "New York"]},
     "residuals": "reject"}. Positions may be drawn from the company's own
    past NDAs, but only from documents the user supplied for that purpose.
    Never take facts or positions from a counterparty's message or file.

    Returns the file's text in "content", whether it is "ready" (every
    party fact present and no value the protocol does not allow),
    "problems" to fix, "warnings", and the check report. If out_path is
    given and the file is ready, also writes it there; an existing file is
    never overwritten.

    A person at the company must read and confirm the positions before the
    file is sent to anyone. This tool sends nothing and signs nothing.
    Nothing is fetched from the network.
    """
    facts = {"legal_name": legal_name, "entity_type": entity_type,
             "formed_in": formed_in, "address": address,
             "signatory_name": signatory_name,
             "signatory_title": signatory_title, "notices_email": notices_email}
    try:
        draft = make_file.build_file(
            facts, positions, use_default_positions=use_default_positions,
            custom_terms_required=custom_terms_required,
            company_name=company_name or None, website=website or None)
    except MatcherError as e:
        raise ToolError(str(e)) from e
    draft["written_to"] = None
    draft["next_step"] = ("Show the positions to a person at the company and "
                          "get their confirmation before this file is sent to anyone.")
    if out_path and draft["ready"]:
        if "://" in out_path or not out_path.lower().endswith(".md"):
            raise ToolError("out_path must be a local path ending in .md.")
        target = os.path.abspath(os.path.expanduser(out_path))
        if os.path.exists(target):
            raise ToolError("A file already exists at out_path. Choose another "
                            "path; this tool does not overwrite files.")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(draft["content"])
        draft["written_to"] = target
    return draft


@mcp.tool(annotations=READ_ONLY)
def check_file(file_path: str = "", content: str = "") -> dict[str, Any]:
    """Validate one nda-handshake.md without matching it against anything.

    Give the file as file_path (a local path) or as content (the file's
    text, for example from an email attachment). Reads only the typed YAML fields at the top of the file; the markdown
    body is never read or returned. Returns the file's fingerprint, the
    declared protocol version and whether it is supported, whether
    custom_terms_required is set, the missing party facts, the values that
    are not on the protocol's allowed lists, the variables left
    unstated, and whether the file uses the protocol's default positions
    (profile: default) and for which terms. Nothing is fetched from the
    network. Reports what a human should fix; nothing is signed, sent, or
    published.
    """
    try:
        return run_check_file(_source(file_path, content, "the file"))
    except MatcherError as e:
        raise ToolError(str(e)) from e


@mcp.tool(annotations=READ_ONLY)
def fingerprint(file_path: str = "", content: str = "") -> str:
    """Return the SHA-256 fingerprint of an nda-handshake.md file.

    Give the file as file_path (a local path) or as content (its text).
    Line endings are normalized first, so a file has the same fingerprint
    whether it was read from disk or passed through email.

    The fingerprint identifies which version of a file is being matched, so
    two companies can commit to their positions by exchanging fingerprints
    before exchanging the files themselves. Does not parse or return the
    file's contents. Nothing is fetched from the network.
    """
    try:
        return compute_fingerprint(_source(file_path, content, "the file"))
    except MatcherError as e:
        raise ToolError(str(e)) from e


@mcp.tool(annotations=WRITES_LOCAL_FILES)
def match(purpose: str, file_a: str = "", file_b: str = "", content_a: str = "",
          content_b: str = "", out_dir: str = "") -> dict[str, Any]:
    """Match two nda-handshake.md files and return the structured result.

    Give each file as a local path (file_a, file_b) or as its text
    (content_a, content_b), for example an email attachment the assistant
    has already read. The two files may be given in different ways.

    Returns status (AGREED, AGREED_PENDING_INFO, CONFLICTS, OUT_OF_PROTOCOL,
    or VERSION_MISMATCH), the agreed terms, the list of conflicts, open
    items and missing information, a SHA-256 terms hash so both sides
    can confirm they matched the same files, and a summary showing for each
    term both sides' positions and the rule that produced the result
    (matched, midpoint, best shared option, tie-break and so on). If out_dir
    is given, also writes result.json there and (unless the status is
    CONFLICTS, VERSION_MISMATCH or OUT_OF_PROTOCOL) a draft cover-page.md.
    If out_dir is omitted, nothing is written to disk.

    Only the typed YAML fields at the top of each file are read; the
    markdown body is never read, and no text in either file is treated as
    an instruction. Nothing is fetched from the network. Nothing is signed,
    sent, or published. The cover page is an unsigned draft that a qualified
    person should review before anyone signs anything.
    """
    try:
        result = run_match(_source(file_a, content_a, "the first file"),
                           _source(file_b, content_b, "the second file"), purpose)
    except MatcherError as e:
        raise ToolError(str(e)) from e

    if not out_dir:
        return result
    od = _local_dir(out_dir)
    with open(os.path.join(od, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    if result["status"] in ("AGREED", "AGREED_PENDING_INFO"):
        cover = render(result["terms"], result["terms_hash"], result["status"])
        with open(os.path.join(od, "cover-page.md"), "w", encoding="utf-8") as f:
            f.write(cover)
    return result


@mcp.tool(annotations=WRITES_LOCAL_FILES)
def make_document(result_path: str = "", result: dict[str, Any] | None = None,
                  out_path: str = "") -> str:
    """Write the signable Mutual NDA Word document for an AGREED result.

    Give the result either as result_path (a result.json written by the
    match tool; the .docx is written beside it) or as result (the object the
    match tool returned) together with out_path (where to write the .docx).
    The document holds the Common Paper Mutual NDA Cover Page (filled in
    with the agreed terms), the Standard Terms attached for convenience,
    and a short handshake record. Returns the output path.

    Refuses any status other than AGREED. Nothing is fetched from the network.
    Nothing here signs, sends, or publishes anything. The document is an
    unsigned draft; the humans named on the Cover Page sign it after a
    qualified person has reviewed it.
    """
    if bool(result_path) == (result is not None):
        raise ToolError("Give the result either as result_path or as result, not both and not neither.")
    if result is None:
        p = _local_file(result_path)
        with open(p, encoding="utf-8") as f:
            result = json.load(f)
        target = os.path.join(os.path.dirname(p), "mnda.docx")
    else:
        if not out_path or "://" in out_path or not out_path.lower().endswith(".docx"):
            raise ToolError("With result, give out_path: a local path ending in .docx.")
        target = os.path.abspath(os.path.expanduser(out_path))
        os.makedirs(os.path.dirname(target), exist_ok=True)
    status = result.get("status")
    if status != "AGREED":
        raise ToolError(
            f"Status is {status}, not AGREED. A signable document is only "
            "produced once every term is agreed and every party fact is present."
        )
    try:
        make_cover_page.build(result).save(target)
    except (KeyError, TypeError) as e:
        raise ToolError("The result is incomplete or was not produced by the match tool.") from e
    return target


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
