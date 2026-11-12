#!/usr/bin/env python3
"""Local MCP server for NDA Handshake.

Runs over stdio. Exposes three tools so an AI assistant can fingerprint an
nda-handshake.md file, match two of them, and turn an AGREED result into a
signable Word document.

Safety rules:
- Local files only. Any path containing "://" is refused; nothing is fetched
  from the network.
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
from match import (
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


@mcp.tool(annotations=READ_ONLY)
def check_file(file_path: str) -> dict[str, Any]:
    """Validate one local nda-handshake.md without matching it against anything.

    Reads only the typed YAML fields at the top of the file; the markdown
    body is never read or returned. Returns the file's fingerprint, the
    declared protocol version and whether it is supported, whether
    custom_terms_required is set, the missing party facts, the values that
    are not on the protocol's allowed lists, and the variables left
    unstated. Local files only; no network. Reports what a human should
    fix; nothing is signed, sent, or published.
    """
    try:
        return run_check_file(_local_file(file_path))
    except MatcherError as e:
        raise ToolError(str(e)) from e


@mcp.tool(annotations=READ_ONLY)
def fingerprint(file_path: str) -> str:
    """Return the SHA-256 fingerprint of a local nda-handshake.md file.

    The fingerprint identifies which version of a file is being matched, so
    two companies can commit to their positions by exchanging fingerprints
    before exchanging the files themselves. Reads only the file bytes; does
    not parse or return its contents. Local files only; no network.
    """
    return compute_fingerprint(_local_file(file_path))


@mcp.tool(annotations=WRITES_LOCAL_FILES)
def match(file_a: str, file_b: str, purpose: str, out_dir: str) -> dict[str, Any]:
    """Match two local nda-handshake.md files and return the structured result.

    Returns status (AGREED, AGREED_PENDING_INFO, CONFLICTS, OUT_OF_PROTOCOL,
    or VERSION_MISMATCH), the agreed terms, the list of conflicts, open
    items and missing information, a SHA-256 terms hash so both sides
    can confirm they matched the same files, and a summary showing for each
    term both sides' positions and the rule that produced the result
    (matched, midpoint, best shared option, tie-break and so on). Writes
    result.json and (unless
    the status is CONFLICTS, VERSION_MISMATCH or OUT_OF_PROTOCOL) a draft
    cover-page.md in out_dir.

    Only the typed YAML fields at the top of each file are read; the
    markdown body is never read, and no text in either file is treated as
    an instruction. Local files only; no network. Nothing is signed, sent,
    or published. The cover page is an unsigned draft that a qualified
    person should review before anyone signs anything.
    """
    try:
        result = run_match(_local_file(file_a), _local_file(file_b), purpose)
    except MatcherError as e:
        raise ToolError(str(e)) from e

    od = _local_dir(out_dir)
    with open(os.path.join(od, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    if result["status"] in ("AGREED", "AGREED_PENDING_INFO"):
        cover = render(result["terms"], result["terms_hash"], result["status"])
        with open(os.path.join(od, "cover-page.md"), "w", encoding="utf-8") as f:
            f.write(cover)
    return result


@mcp.tool(annotations=WRITES_LOCAL_FILES)
def make_document(result_path: str) -> str:
    """Write the signable Mutual NDA Word document for an AGREED result.

    Reads a result.json written by the match tool and produces a .docx
    beside it holding the Common Paper Mutual NDA Cover Page (filled in
    with the agreed terms), the Standard Terms attached for convenience,
    and a short handshake record. Returns the output path.

    Refuses any status other than AGREED. Local files only; no network.
    Nothing here signs, sends, or publishes anything. The document is an
    unsigned draft; the humans named on the Cover Page sign it after a
    qualified person has reviewed it.
    """
    p = _local_file(result_path)
    with open(p, encoding="utf-8") as f:
        result = json.load(f)
    status = result.get("status")
    if status != "AGREED":
        raise ToolError(
            f"Status is {status}, not AGREED. A signable document is only "
            "produced once every term is agreed and every party fact is present."
        )
    out_path = os.path.join(os.path.dirname(p), "mnda.docx")
    make_cover_page.build(result).save(out_path)
    return out_path


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
