<img src="icon.png" alt="" width="96" align="right">

# NDA Handshake

Two companies' AI assistants put a standard mutual NDA in place over three
emails, with no redlines.

Status: experimental. Protocol v0.6. This is not legal advice.

## The idea

Most NDAs between companies say nearly the same thing, yet each one still
costs days of back and forth. NDA Handshake removes that step for the
routine case.

Each company writes down, once, the NDA terms it is willing to sign. When
two companies need an NDA, their assistants exchange three short emails
and both arrive at the same agreement, built on the
[Common Paper Mutual NDA](https://commonpaper.com/standards/mutual-nda/1.0).
People still decide to start, and people still sign.

## What it looks like

You tell your assistant:

> Start an NDA handshake with jane@acme.example about a possible partnership.

| Who | What the person does | What the assistant does |
|---|---|---|
| You | Say that one sentence | Seals your positions and sends the invitation |
| Acme | Answers one question: reply to this invitation? | Sends Acme's positions |
| You | Nothing | Works out the NDA, sends the result, tells you the terms |
| Acme | Nothing | Checks the result independently, tells Acme the terms |
| Both | Sign your own copy | |

The emails are written for the people who receive them, with a short block
at the end for the assistants:

    Hello,

    Before we get into the details, Harbor Example LLC would like to put a
    mutual NDA in place. We use NDA Handshake, an open protocol that lets our
    assistants settle a standard NDA so nobody has to trade redlines.

    What we would like to discuss: Evaluating a possible partnership

    Neither side sees the other's positions first, so there is no peeking and
    no haggling. If your assistant already knows NDA Handshake, just ask it to
    handle this email.

    New to it? The page below shows how to add it. It takes a few minutes, and
    your assistant can work out your positions from NDAs you have already
    signed. Or simply reply and we will send a draft the old-fashioned way.

    --- for the assistants (please leave this part as it is) ---
    nda-handshake: invitation
    ...

## Why you can rely on the result

- **Sealed.** The inviting company first sends only a locked commitment to
  its positions. It opens them after the other side has sent its own.
  Neither side can shape its positions around the other's.
- **Fixed rules, not judgment.** The NDA is worked out by a small set of
  published rules. No AI decides any term. The same two sets of positions
  always produce the same NDA.
- **Checked by both sides.** Each side runs the rules itself and compares
  a fingerprint of the result. A changed file or a different answer is
  caught, and nothing is treated as agreed.
- **Bounded.** Only nine terms can vary, and you are never taken outside
  the positions you wrote down. Everything else is the standard form,
  unchanged.
- **Yours.** It runs on your own computer. Nothing is fetched from the
  network, nothing is sent without you, and nothing is signed for you.
- **Open.** The protocol, the rules and this implementation are public.
  Anyone can build a compatible one and check it against the same examples.

It has been run end to end between two different AI assistants on separate
machines, each verifying the other's result.

## The nine terms

The length of the NDA, the confidentiality period and when it starts,
governing law, venue, whether confidential material must be marked, a
residuals clause, sharing with affiliates, and the standard form itself.
A company can take the protocol's balanced default positions with one
line, or set its own. `GUIDE.md` walks through each choice in plain
English.

If two companies' positions do not meet, there is no NDA from the
handshake. Each assistant tells its own person which terms failed, with a
suggestion, and the people take it from there. Assistants do not bargain
with each other. If a company needs something the protocol leaves out,
such as a non-solicit or a one-way NDA, the handshake says so and steps
aside.

## Get started

1. **Install it.** Download `nda-handshake-<version>.mcpb` from the
   [Releases page](https://github.com/Ivolver/NDA-Handshake/releases) and
   open it in Claude Desktop. It asks where to keep your files and installs
   itself. Other assistants can run it from the source; see
   "Install by hand" below.
2. **Set up your company.** Say "Set up NDA Handshake for my company." Your
   assistant asks for the company's details and offers three ways to set
   your NDA positions: take the balanced defaults, hand it a few NDAs your
   company has signed (or your own template) and let it propose positions
   from them, or go through the nine choices one at a time. It shows you
   every position, and where each came from, and saves your file once you
   confirm.

If you received an invitation and do not have NDA Handshake yet, do those
two steps and then ask your assistant to handle the invitation.
3. **Start a handshake**, or ask your assistant to handle an invitation
   you received.

Install it only from the Releases page or a connector directory you
already trust, never from a link in an email.

## Read more

- `GUIDE.md`: writing your company's file, one choice at a time.
- `SPEC.md`: the protocol. The file format, the nine terms, what is
  excluded, the matching rules and the sealed exchange.

The rest of this page is for people who want to run the pieces directly or
build their own implementation.

## Run it

Requires Python 3.10 or newer. To install everything the project uses:

    pip install -r requirements.txt

The matcher alone needs only PyYAML.

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

To run whole sealed exchanges between the example companies, including
the cases where a file or a hash has been tampered with:

    python3 check_sealed.py

## Use with an AI assistant

`mcp_server.py` is a local Model Context Protocol server. An AI assistant
that speaks MCP (for example Claude Desktop) can use it to run a handshake.
Seven tools. Nothing is fetched from the network. The server also gives
the assistant standing instructions, so the person does not have to spell
out the steps.

The front door:

- `handshake(...)`: the assistant calls this and does what the result
  says. Given a purpose and a counterparty, it starts a handshake and
  returns the invitation to send. Given the text of an email that contains
  an `nda-handshake:` block, it works out the step: it replies to an
  invitation, reveals after a reply, or checks a reveal. Given nothing, it
  reports what is set up and which exchanges are in progress. Each result
  says what to tell the person, what to ask them if anything, and the
  exact email to send.

What this looks like to the people involved:

| Who | What the person does | What the assistant does |
|---|---|---|
| Inviter | Says "start an NDA handshake with Jane at Acme about a possible partnership" | Seals the file and sends the invitation |
| Replier | Answers one question: reply to this invitation? | Sends the reply with the company's file |
| Inviter | Nothing | Runs the match, sends the reveal (with the NDA attached if it can), reports the terms |
| Replier | Nothing | Verifies the reveal, reports the terms |
| Both | Sign their copy of the NDA | |

Only two things ever need a person's yes: replying to an invitation, since
it shares the company's positions, and sending a contest.

Setting up:

- `setup(storage_folder)`: one-time choice of the folder where the company
  keeps its own `nda-handshake.md` and its completed NDAs.
- `draft_file(party facts, positions, out_path)`: the onboarding step.
  Writes a company's own `nda-handshake.md` from its seven party facts and
  either the default positions or positions the assistant collected, for
  example from the company's own past NDAs. Returns the file's text and a
  check report, plus each position in plain English for the person to
  confirm. With `save`, stores it as the company's own file.

Working with files directly:

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

All seven return structured output only. No tool returns the body text of
a file it was given, or the contents of any other file; `draft_file`
returns only the text it wrote itself. Every
output is an unsigned draft that a qualified person should review before
anyone signs anything.

### Install with one click

Download `nda-handshake-<version>.mcpb` from the project's
[Releases page](https://github.com/Ivolver/NDA-Handshake/releases) and open
it, or drag it into the Extensions settings of Claude Desktop. The app
shows what the connector does, asks which folder should hold your
company's file and your completed NDAs, and installs it. The app manages
Python and the packages the connector needs; you do not need to install
anything else or use a terminal.

Install it only from that Releases page or from a connector directory you
already trust. Do not install it from a link in an email, including an NDA
Handshake invitation.

### Install by hand

For other assistants, or to run from the source. Requires Python 3.10 or
newer and the packages in `requirements.txt`:

    pip install -r requirements.txt

To add the server to Claude Desktop this way, add an `nda-handshake` entry
under `mcpServers` in its config file, pointing `command` at a Python with
the packages installed and `args` at `mcp_server.py` in this folder. The
config file lives at `~/Library/Application Support/Claude/claude_desktop_config.json`
on macOS. Restart Claude Desktop to pick up the change. An assistant that
cannot add connectors to its own tools can still take part by running
`mcp_server.py` from a command line and calling its tools.

### Build the one-click bundle

The bundle is described by `manifest.json`, `pyproject.toml` and
`.mcpbignore`. To build it with the official packaging tool:

    npx @anthropic-ai/mcpb pack . dist/nda-handshake-<version>.mcpb

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
