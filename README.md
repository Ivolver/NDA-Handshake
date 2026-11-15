<img src="icon.png" alt="" width="96" align="right">

# NDA Handshake

Two companies' AI assistants put a standard mutual NDA in place over three
emails, with no redlines and no signature round.

Protocol v0.7. This is not legal advice.

## The idea

Most NDAs between companies say nearly the same thing, yet each one still
costs days of back and forth. NDA Handshake removes that step for the
routine case.

Each company writes down, once, the NDA terms it is willing to accept, and
a person with authority approves them in advance. When two companies need
an NDA, their assistants exchange three short emails and both arrive at
the same agreement, built on the
[Common Paper Mutual NDA](https://commonpaper.com/standards/mutual-nda/1.0).
If the two sets of positions meet, the NDA is in place when the third
email is sent. Nobody opens a document to sign it. People still decide to
start, and people set every position.

## What it looks like

You tell your assistant:

> Start an NDA handshake with jane@acme.example about a possible partnership.

| Who | What the person does | What the assistant does |
|---|---|---|
| You | Say that one sentence | Seals your positions and sends the invitation |
| Acme | Answers one question: reply to this invitation? | Sends Acme's positions |
| You | Nothing | Works out the NDA and sends the result. The NDA is now in place. Tells you the terms |
| Acme | Nothing | Checks the result independently within one business day, tells Acme the terms |

The emails are written for the people who receive them, with a short block
at the end for the assistants:

    Hello,

    Before we get into the details, Harbor Example LLC would like to put a
    mutual NDA in place. We use NDA Handshake, an open protocol that lets our
    assistants settle a standard NDA so nobody has to trade redlines.

    What we would like to discuss: Evaluating a possible partnership

    Neither side sees the other's positions first, so there is no peeking and
    no haggling. If the positions meet, the NDA is in place right then. Nobody
    has to sign anything, because each company approves its positions in
    advance. If your assistant already knows NDA Handshake, just ask it to
    handle this email.

    New to it? The page below shows how to add it. It takes a few minutes, and
    your assistant can work out your positions from NDAs you have already
    signed. Or simply reply and we will send a draft the old-fashioned way.

    --- for the assistants (please leave this part as it is) ---
    nda-handshake: invitation
    ...

## No signature each time

When a company sets up, a person with authority to bind it to NDAs reads
one fixed confirmation and types their name and title. It says, in short:
any NDA a handshake produces inside the positions in this file is approved
for the company and is executed when the exchange completes, and I have
authority to say so. That is the only approval. From then on:

- The other company's reply is an offer. Your assistant's result email is
  the acceptance, and the NDA is formed when it is sent.
- The replying company has one business day to object, and only to a real
  mismatch: an altered file, a different result, or an email that did not
  come from where the other company's file says it is sent from.
- The result email says the NDA has been executed, and the NDA document
  carries both signatures. Each is simply "/s/" and the company's legal
  name, with the person and date of that company's confirmation beneath.
- The confirmation covers the positions in the file on the day it was
  given. Change a position and it has to be given again.

A company that would rather sign each NDA by hand does not give the
confirmation. It cannot use a handshake, and gets an ordinary draft on the
same standard form instead. The full text of the confirmation is in
`forms/confirmation/confirmation.md`, and `SPEC.md` explains the legal
basis and its limits. Have your own counsel read it before you confirm.

## Why you can rely on the result

- **Sealed.** The inviting company first sends only a locked commitment to
  its positions. It opens them after the other side has sent its own.
  Neither side can shape its positions around the other's.
- **Fixed rules, not judgment.** The NDA is worked out by a small set of
  published rules. No AI decides any term. The same two sets of positions
  always produce the same NDA.
- **Checked by both sides.** Each side runs the rules itself and compares
  a fingerprint of the result. A changed file or a different answer is
  caught and contested, and then there is no NDA.
- **Bounded.** Only nine terms can vary, and you are never taken outside
  the positions you confirmed. Everything else is the standard form,
  unchanged.
- **Tied to the company.** A company's file says which email domain or
  address it is sent from. A file arriving from anywhere else stops the
  handshake.
- **Yours.** It runs on your own computer. Nothing is fetched from the
  network and nothing is sent without you. No assistant can give your
  company's confirmation; only a person typing their own name can.
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
   [latest release](https://github.com/Ivolver/NDA-Handshake/releases/latest) and
   open it in Claude Desktop. It asks where to keep your files and installs
   itself. Other assistants can run it from the source; see
   "Install by hand" below.
2. **Set up your company.** Say "Set up NDA Handshake for my company." Your
   assistant asks for the company's details and offers three ways to set
   your NDA positions: take the balanced defaults, hand it a few NDAs your
   company has signed (or your own template) and let it propose positions
   from them, or go through the nine choices one at a time. It shows you
   every position, and where each came from, and saves your file once you
   agree.
3. **Give the confirmation.** Your assistant shows you the confirmation
   text. A person with authority to bind the company reads it and types
   their name and title. This is the step that replaces signing each NDA.

If you received an invitation and do not have NDA Handshake yet, do those
three steps and then ask your assistant to handle the invitation.
4. **Start a handshake**, or ask your assistant to handle an invitation
   you received.

Install it only from the project's Releases page or a connector directory
you already trust, never from a link in an email.

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

To see what happens when a company has not given its confirmation
(expected status `AGREED_PENDING_INFO`, with the confirmation listed as
missing):

    python3 match.py examples/harbor-fictional/nda-handshake.md examples/tidewater-fictional/nda-handshake.md \
        --purpose "Evaluating a potential business relationship" \
        --out out/harbor-tidewater

Running the matcher by hand executes nothing. An NDA is executed only
through the sealed exchange.

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

## Make a copy of the document

A handshake writes the executed NDA into each company's deal folder. To
turn a bare `AGREED` match result into a Word document by hand (requires
`pip install python-docx`):

    python3 make_cover_page.py out/harbor-lakeside/result.json

This writes the document next to the result, named for both companies (for
example `MNDA_Harbor-Example-LLC_and_Lakeside-Example-LLC.docx`; an executed
NDA starts with its date, as in `2026-11-14_MNDA_...`). It holds the Common Paper Cover
Page filled in with the agreed terms, the Standard Terms attached for
convenience, and a one-page handshake record that is not part of the
agreement. The record shows how each term was reached. A copy made this
way, outside a completed handshake, is marked "Not executed". Any other
status produces no document.

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
Nine tools. Nothing is fetched from the network. The server also gives
the assistant standing instructions, so the person does not have to spell
out the steps.

The front door:

- `handshake(...)`: the assistant calls this and does what the result
  says. Given a purpose and a counterparty, it starts a handshake and
  returns the invitation to send. Given the text of an email that contains
  an `nda-handshake:` block and the address it came from, it works out
  the step: it replies to an invitation, reveals after a reply, or checks
  a reveal. Given nothing, it
  reports what is set up and which exchanges are in progress. Each result
  says what to tell the person, what to ask them if anything, and the
  exact email to send.

What this looks like to the people involved:

| Who | What the person does | What the assistant does |
|---|---|---|
| Inviter | Says "start an NDA handshake with Jane at Acme about a possible partnership" | Seals the file and sends the invitation |
| Replier | Answers one question: reply to this invitation? | Sends the reply with the company's file |
| Inviter | Nothing | Runs the match, sends the reveal (with the NDA attached if it can), reports the terms. The NDA is executed when the reveal is sent |
| Replier | Nothing | Verifies the reveal within one business day, reports the terms |

Only two things in an exchange ever need a person's yes: replying to an
invitation, since it shares the company's positions and offers the NDA,
and sending a contest. The confirmation is given once, before any
exchange.

- `draft_nda(purpose, counterparty_name)`: for a counterparty that does not
  use NDA Handshake and asks for a draft the usual way. Writes the standard
  form as a Word document with the company's own preferred positions and
  the counterparty's details left to fill in, plus a short email to send
  with it. An invitation is never wasted: the worst case is an ordinary
  draft on a standard form.

Setting up:

- `setup(storage_folder)`: one-time choice of the folder where the company
  keeps its own `nda-handshake.md` and its completed NDAs.
- `draft_file(party facts, positions, out_path)`: the onboarding step.
  Writes a company's own `nda-handshake.md` from its seven party facts and
  either the default positions or positions the assistant collected, for
  example from the company's own past NDAs. Returns the file's text and a
  check report, plus each position in plain English for the person to
  agree to. With `save`, stores it as the company's own file. A saved file
  has no confirmation yet.
- `confirm()`, then `confirm(typed_name, title)`: the standing
  confirmation. The first call returns the full text for the person to
  read and changes nothing. The second records it in the company's file,
  and only works with the name and title the person typed after being
  shown that text. `sent_from` sets the domain or address the company's
  handshake emails come from. `withdraw` removes the confirmation.

Working with files directly:

- `check_file(file_path or content)`: validates one `nda-handshake.md` on
  its own and reports the declared protocol version, missing party facts,
  values not on the protocol's allowed lists, unstated variables,
  whether `custom_terms_required` is set, and whether the confirmation is
  on file and still covers the positions.
- `fingerprint(file_path or content)`: the SHA-256 of one
  `nda-handshake.md`, with line endings normalized.
- `match(purpose, file_a or content_a, file_b or content_b, out_dir)`: the
  structured result, with status, agreed terms, conflicts, open items,
  missing info and terms hash. `out_dir` is optional. If given, the tool
  also writes `result.json` and, when terms are agreed, `cover-page.md`
  there. If not, nothing is written to disk.
- `make_document(result_path)` or `make_document(result, out_path)`: writes
  a copy of the NDA as a Word document, either next to a saved result or
  at `out_path` from the result the `match` tool returned. Refuses any
  status other than `AGREED`.

All nine return structured output only. No tool returns the body text of
a file it was given, or the contents of any other file; `draft_file`
returns only the text it wrote itself, and `confirm` returns the fixed
confirmation text. Matching two files with `match` executes nothing; an
NDA is executed only through the sealed exchange.

### Install with one click

Download `nda-handshake-<version>.mcpb` from the project's
[latest release](https://github.com/Ivolver/NDA-Handshake/releases/latest) and open
it, or drag it into the Extensions settings of Claude Desktop. The app
shows what the connector does, asks which folder should hold your
company's file and your completed NDAs, and installs it. The app manages
Python and the packages the connector needs; you do not need to install
anything else or use a terminal.

Install it only from the project's Releases page or from a connector directory you
already trust. Do not install it from a link in an email, including an NDA
Handshake invitation.

### Install as a plugin

In Claude Code, and in Cowork sessions that run on your own computer, NDA
Handshake installs as a plugin. The plugin starts the same connector and
adds a short skill that tells the assistant when to use it. It needs
[uv](https://docs.astral.sh/uv/) on your computer to run the connector. In
Claude Code:

    /plugin install nda-handshake --marketplace Ivolver/NDA-Handshake

In the Claude desktop app, add the repository under Customize, Plugins.
The plugin does not ask for a storage folder when it installs. The
assistant asks for one the first time, through the `setup` tool. An
ordinary chat cannot start a plugin's local connector, so for chat use the
one-click bundle above.

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
3. Have your own counsel read the confirmation text and your positions
   before a person with authority gives the confirmation. After that,
   NDAs inside those positions are executed without further review.

## Privacy

NDA Handshake runs entirely on your own computer.

- **What it collects:** nothing. There is no account, no telemetry and no
  analytics. The project's authors receive no information about you, your
  company, your positions or your NDAs.
- **What it stores, and where:** your company's `nda-handshake.md` and your
  completed NDAs in the storage folder you choose, and a small record of
  each exchange in a `.nda-handshake` folder in your home directory. All
  of it stays on your computer until you delete it.
- **What it sends:** nothing. The connector makes no network requests. The
  emails of an exchange are sent by your assistant through your own email,
  with your approval, and they go only to the counterparty you chose. An
  exchange shares your company's positions with that counterparty; that is
  its purpose, and your assistant asks before replying to an invitation.
  When an NDA is executed, your assistant also emails a record copy to
  your own company's notices address.
- **Third parties:** none on the project's side. Your AI assistant and your
  email provider handle the content of your conversations and emails under
  their own terms. A one-click install lets the app download Python and
  the open-source packages the connector needs.
- **Questions:** open an issue at
  https://github.com/Ivolver/NDA-Handshake/issues.

## Disclaimer

This tool is not legal advice. Using it creates no attorney-client
relationship. An NDA made by handshake is executed under each company's
standing confirmation without anyone reviewing that NDA, so a qualified
person should review the confirmation text and the company's positions
before the confirmation is given. No reported United States decision yet
addresses a contract concluded this way.

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
