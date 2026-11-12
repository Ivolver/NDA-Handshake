#!/usr/bin/env python3
"""Exercise every tool in mcp_server.py over a real stdio transport.

Launches mcp_server.py as an MCP subprocess, calls fingerprint, match (on
the AGREED pair and the CONFLICTS pair), and make_document (on the AGREED
result and, to show the refusal, on the CONFLICTS result). Prints "ok" per
case and exits non-zero on the first failure.
"""
import asyncio
import json
import os
import shutil
import sys
import tempfile

from mcp import Client, StdioServerParameters

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, "examples")
PURPOSE = "Evaluating a potential business relationship"

EXPECTED_FINGERPRINTS = json.load(
    open(os.path.join(EXAMPLES, "expected-results.json"), encoding="utf-8")
)["fingerprints"]


def _text(result) -> str:
    """Join the text content of a tool result, preferring structured output."""
    if result.structured_content is not None:
        return json.dumps(result.structured_content)
    return "".join(block.text for block in result.content if getattr(block, "text", None))


def _structured(result):
    sc = result.structured_content
    if sc is None:
        return None
    # The SDK wraps non-model returns as {"result": value}.
    return sc.get("result", sc) if isinstance(sc, dict) and set(sc.keys()) == {"result"} else sc


async def run() -> int:
    params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(HERE, "mcp_server.py")],
        cwd=HERE,
    )
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        status = "ok  " if condition else "FAIL"
        print(f"{status}  {name}" + (f": {detail}" if not condition and detail else ""))
        if not condition:
            failures.append(name)

    async with Client(params, raise_exceptions=True) as client:
        tool_names = sorted(t.name for t in (await client.list_tools()).tools)
        check("list_tools returns the four tools",
              tool_names == ["check_file", "fingerprint", "make_document", "match"],
              f"got {tool_names}")

        harbor_md = os.path.join(EXAMPLES, "harbor-fictional", "nda-handshake.md")
        lakeside_md = os.path.join(EXAMPLES, "lakeside-fictional", "nda-handshake.md")
        northwind_md = os.path.join(EXAMPLES, "northwind-fictional", "nda-handshake.md")

        # fingerprint, cross-checked against examples/expected-results.json
        fp = _structured(await client.call_tool("fingerprint", {"file_path": harbor_md}))
        want = EXPECTED_FINGERPRINTS["harbor-fictional/nda-handshake.md"]
        check("fingerprint matches expected-results.json for harbor",
              fp == want, f"got {fp}, want {want}")

        # check_file on a valid example: nothing missing, nothing unstated.
        valid = _structured(await client.call_tool("check_file", {"file_path": harbor_md}))
        check("check_file on harbor: protocol version supported",
              valid["protocol_version_supported"])
        check("check_file on harbor: no missing party facts",
              valid["missing_party_facts"] == [],
              f"got {valid['missing_party_facts']}")
        check("check_file on harbor: no bad values",
              valid["bad_values"] == [], f"got {valid['bad_values']}")
        check("check_file on harbor: no unstated variables",
              valid["unstated_variables"] == [],
              f"got {valid['unstated_variables']}")
        check("check_file on harbor: no body text in the report",
              "A made-up company" not in json.dumps(valid))

        with tempfile.TemporaryDirectory() as tmp:
            # check_file on a deliberately incomplete temporary file.
            incomplete_md = os.path.join(tmp, "incomplete.md")
            with open(incomplete_md, "w", encoding="utf-8") as f:
                f.write(
                    "---\n"
                    'nda_handshake: "0.3"\n'
                    "company:\n  name: Incomplete Example (fictional)\n"
                    "entities:\n"
                    "  - id: inc\n"
                    "    default: true\n"
                    "    legal_name: Incomplete Example LLC\n"
                    "    entity_type: limited liability company\n"
                    "    formed_in: TODO\n"
                    "    address: TODO\n"
                    "signatory:\n  name: TODO\n  title: TODO\n"
                    "notices:\n  email: TODO\n"
                    "nda:\n"
                    "  form:\n    prefer: common-paper-mnda-1.0\n"
                    "    accept: [common-paper-mnda-1.0]\n"
                    "  governing_law:\n    prefer: Atlantis\n"
                    "    accept: [Atlantis]\n"
                    "  residuals: maybe\n"
                    "---\n\n"
                    "# Incomplete Example LLC\n"
                )
            report = _structured(await client.call_tool(
                "check_file", {"file_path": incomplete_md}))
            check("check_file on incomplete: protocol version still supported",
                  report["protocol_version_supported"])
            check("check_file on incomplete: flags every TODO party fact",
                  {"Party: formed_in", "Party: address",
                   "Party: signatory_name", "Party: signatory_title",
                   "Party: notice_email"}.issubset(set(report["missing_party_facts"])),
                  f"got {report['missing_party_facts']}")
            check("check_file on incomplete: flags Atlantis as not on the US-state list",
                  any("Atlantis" in bv for bv in report["bad_values"]),
                  f"got {report['bad_values']}")
            check("check_file on incomplete: flags residuals 'maybe' as not require/accept/reject",
                  any("residuals" in bv and "maybe" in bv for bv in report["bad_values"]),
                  f"got {report['bad_values']}")
            check("check_file on incomplete: lists unstated variables",
                  set(report["unstated_variables"]) >= {
                      "venue", "marking_requirement", "confidentiality_starts",
                      "nda_term_years", "confidentiality_years",
                      "affiliate_sharing",
                  }, f"got {report['unstated_variables']}")

            # match on the AGREED pair
            agreed = _structured(await client.call_tool("match", {
                "file_a": harbor_md, "file_b": lakeside_md,
                "purpose": PURPOSE, "out_dir": os.path.join(tmp, "harbor-lakeside"),
            }))
            check("match AGREED pair returns AGREED",
                  agreed["status"] == "AGREED", f"status {agreed['status']}")
            check("match AGREED pair wrote result.json and cover-page.md",
                  os.path.isfile(os.path.join(tmp, "harbor-lakeside", "result.json"))
                  and os.path.isfile(os.path.join(tmp, "harbor-lakeside", "cover-page.md")))
            check("match AGREED result has no body text",
                  "A made-up company" not in json.dumps(agreed))

            # match on the CONFLICTS pair
            conflicting = _structured(await client.call_tool("match", {
                "file_a": harbor_md, "file_b": northwind_md,
                "purpose": PURPOSE, "out_dir": os.path.join(tmp, "harbor-northwind"),
            }))
            check("match CONFLICTS pair returns CONFLICTS",
                  conflicting["status"] == "CONFLICTS",
                  f"status {conflicting['status']}")
            check("match CONFLICTS pair reports four conflicts",
                  len(conflicting["conflicts"]) == 4,
                  f"got {len(conflicting['conflicts'])}")
            check("match CONFLICTS pair did not write cover-page.md",
                  not os.path.exists(os.path.join(tmp, "harbor-northwind", "cover-page.md")))

            # make_document on the AGREED result writes mnda.docx
            agreed_result_json = os.path.join(tmp, "harbor-lakeside", "result.json")
            doc_path = _structured(await client.call_tool(
                "make_document", {"result_path": agreed_result_json}))
            check("make_document returned a path ending in mnda.docx",
                  isinstance(doc_path, str) and doc_path.endswith("mnda.docx"))
            check("make_document wrote the file",
                  os.path.isfile(doc_path) and os.path.getsize(doc_path) > 1000)

            # make_document on a CONFLICTS result refuses
            conflict_result_json = os.path.join(tmp, "harbor-northwind", "result.json")
            refused = await client.call_tool(
                "make_document", {"result_path": conflict_result_json})
            is_error = bool(getattr(refused, "is_error", False))
            msg = _text(refused)
            check("make_document refuses a CONFLICTS result",
                  is_error and "not AGREED" in msg, f"isError={is_error}, msg={msg[:120]}")

            # A URL is refused by the local-file guard
            urled = await client.call_tool("fingerprint",
                                           {"file_path": "https://example.com/x.md"})
            check("fingerprint refuses a URL",
                  bool(getattr(urled, "is_error", False))
                  and "URL" in _text(urled).upper(),
                  _text(urled)[:120])

    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("All MCP tool checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
