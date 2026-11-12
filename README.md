# NDA Handshake (protocol v0.5)

Status: experimental. Protocol v0.5.

Two companies exchange `nda-handshake.md` files. A matcher works out the NDA terms
both can accept and drafts the cover page. Humans sign.

A company that sends its file first shows its positions to the other side.
`SPEC.md` explains how to exchange files fairly today, and a sealed exchange
procedure that builds this in is planned.

See `SPEC.md` for the protocol: the file format, the closed list of
negotiable terms, what is excluded, and the matching rules. When writing
your own file, start with `GUIDE.md`, which walks through each of the nine
choices in plain English.

## Run it

Requires Python 3 and PyYAML (`pip install pyyaml`).

    python3 match.py examples/harbor-fictional/nda-handshake.md examples/lakeside-fictional/nda-handshake.md \
        --purpose "Evaluating a potential business relationship" \
        --out out/harbor-lakeside

Outputs in the `--out` folder:

- `result.json`: status, agreed terms, conflicts, missing info, open items,
  terms hash and file fingerprints
- `cover-page.md`: draft cover page (not written unless terms are agreed)

To see the conflict path (expected status `CONFLICTS`, four conflicts):

    python3 match.py examples/harbor-fictional/nda-handshake.md examples/northwind-fictional/nda-handshake.md \
        --purpose "Evaluating a potential business relationship" \
        --out out/harbor-northwind

To see the out-of-protocol path (expected status `OUT_OF_PROTOCOL`):

    python3 match.py examples/harbor-fictional/nda-handshake.md examples/outlier-fictional/nda-handshake.md \
        --purpose "Evaluating a potential business relationship" \
        --out out/harbor-outlier

To see a principled tie-break (two New York companies tie between Delaware
and New York, and the result is New York because both are formed there):

    python3 match.py examples/lakeside-fictional/nda-handshake.md examples/midtown-fictional/nda-handshake.md \
        --purpose "Evaluating a potential business relationship" \
        --out out/lakeside-midtown

To see the default positions (two companies that state no positions of
their own and simply set `profile: default`):

    python3 match.py examples/pioneer-fictional/nda-handshake.md examples/quarry-fictional/nda-handshake.md \
        --purpose "Evaluating a potential business relationship" \
        --out out/pioneer-quarry

Every result includes a `summary` showing, term by term, both sides'
positions, the outcome and the rule that produced it.

To print a file's fingerprint, for exchanging before the files themselves:

    python3 match.py --fingerprint examples/harbor-fictional/nda-handshake.md

## Make the signable document

Once a match returns `AGREED`, turn its result into a Word document
(requires `pip install python-docx`):

    python3 make_cover_page.py out/harbor-lakeside/result.json

This writes `mnda.docx` next to the result. It holds the Common Paper Cover
Page filled in with the agreed terms, the Standard Terms attached for
convenience, and a one-page handshake record that is not part of the
agreement. The record shows how each term was reached. Any other status produces no document.

## Schemas

The `schema/` folder holds JSON Schemas for the two data formats:
`nda-handshake.schema.json` for the fields at the top of an
`nda-handshake.md`, and `result.schema.json` for a matcher's `result.json`.
Use them to validate a file or a result in any language. `SPEC.md` remains
the authority.

The Word document carries its terms hash and protocol version in its
document properties, so software that receives only the document can find
the matching result.

## Check an implementation

`examples/expected-results.json` lists each example pair with its expected
status, terms hash and conflicts, plus each example file's fingerprint. To
check this matcher against it:

    python3 check_examples.py

Anyone building another implementation of the protocol can run the same
example files and compare against the same list. Install `jsonschema`
(optional) to also validate every example and every generated result
against the schemas in `schema/`.

## Use with an AI assistant

`mcp_server.py` is a local Model Context Protocol server. An AI assistant
that speaks MCP (for example Claude Desktop) can use it to run a handshake.
Five tools. Nothing is fetched from the network. Each tool that reads a
file takes it either as a local path or as its text, so an assistant can
work straight from an email attachment without saving anything to disk:

- `draft_file(party facts, positions, out_path)`: the onboarding step.
  Writes a company's own `nda-handshake.md` from its seven party facts and
  either the default positions or positions the assistant collected, for
  example from the company's own past NDAs. Returns the file's text and a
  check report. `out_path` is optional, and an existing file is never
  overwritten. A person at the company confirms the positions before the
  file is sent to anyone.
- `check_file(file_path or content)`: validates one `nda-handshake.md` on
  its own and reports the declared protocol version, missing party facts,
  values not on the protocol's allowed lists, unstated variables, and
  whether `custom_terms_required` is set.
- `fingerprint(file_path or content)`: the SHA-256 of one
  `nda-handshake.md`, with line endings normalized.
- `match(purpose, file_a or content_a, file_b or content_b, out_dir)`: the
  structured result, with status, agreed terms, conflicts, open items,
  missing info and terms hash. `out_dir` is optional. If given, the tool
  also writes `result.json` and, when terms are agreed, `cover-page.md`
  there. If not, nothing is written to disk.
- `make_document(result_path)` or `make_document(result, out_path)`: writes
  the signable Word document, either next to a saved result or at
  `out_path` from the result the `match` tool returned. Refuses any status
  other than `AGREED`.

All five return structured output only. No tool returns the body text of
a file it was given, or the contents of any other file; `draft_file`
returns only the text it wrote itself. Every
output is an unsigned draft that a qualified person should review before
anyone signs anything.

Requires Python 3.10 or newer and the SDK:

    pip install "mcp[cli]" pyyaml python-docx

To add the server to Claude Desktop, open the developer settings
(`Claude > Settings > Developer > Edit Config`) and add an `nda-handshake`
entry under `mcpServers`, pointing `command` at a Python with the three
packages installed and `args` at `mcp_server.py` in this folder. The
config file lives at `~/Library/Application Support/Claude/claude_desktop_config.json`
on macOS. Restart Claude Desktop to pick up the change.

## Before real use

1. Replace every `TODO` in your `nda-handshake.md`.
2. Set your real NDA positions. The sample positions are placeholders.
3. Have the output cover page reviewed and signed by a human.

## Disclaimer

This tool is not legal advice. Using it creates no attorney-client
relationship. The output is an unsigned draft; a qualified person should
review it before anyone signs.

The project references the Common Paper Mutual NDA as a standard form. It is
not affiliated with Common Paper, and Common Paper has not reviewed or
endorsed it.

All companies in the `examples/` folder are fictional. Any resemblance to a
real entity is coincidental.

## License

Code is released under the Apache License, Version 2.0. See `LICENSE` and
`NOTICE`. The specification in `SPEC.md` is licensed under CC BY 4.0.
Copyright 2026 Ultra Vires Labs LLC.

The `forms/common-paper-mnda-1.0/` folder contains the Common Paper Mutual
NDA Standard Terms (Version 1.0), unmodified, which Common Paper releases
under CC BY 4.0. See `SOURCE.md` in that folder.
