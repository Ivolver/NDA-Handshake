# NDA Handshake protocol: spec v0.2 (draft)

Copyright 2026 Ultra Vires Labs LLC. This specification is licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).

## Idea

Before two companies start talking, each shares an `nda-handshake.md`. The file
carries the facts an NDA needs and the company's NDA positions. Software
intersects the two files and produces agreed terms on a standard form. A
human on each side signs. No redlines for the routine case.

The file has its own name so it cannot be confused with a general-purpose
`company.md`. A company that keeps a `company.md` can link to its
`nda-handshake.md` from there.

## Scope

A two-party, mutual NDA between companies, used to evaluate or begin a
commercial relationship, on the Common Paper Mutual NDA v1.0.

Every element of the NDA sits in one of three layers:

- **Fixed:** settled by the standard form for everyone. Not in the file and
  never negotiated.
- **Variable:** the closed list below. Each company states its position and
  the matcher finds the overlap.
- **Excluded:** not available in the protocol. A company that needs one
  flags the deal as out of protocol and negotiates the ordinary way.

## File layout

An `nda-handshake.md` has two parts:

1. A YAML block at the top, between `---` lines. This is the only part
   software reads.
2. A markdown body for humans and for general-purpose agents. The matcher
   never reads it.

## Fields

### nda_handshake
The protocol version the file follows, for example `"0.2"`.

### company
- `name`: common name
- `website`: optional

### entities (list, at least one)
- `id`: short handle, used to choose which entity signs
- `default`: true on the entity that signs unless told otherwise
- `legal_name`: full legal name
- `entity_type`: for example, limited liability company, corporation
- `formed_in`: state or country of formation
- `address`: principal address

### signatory
- `name`, `title`: the human who signs

### notices
- `email`: where legal notices go

### nda: the variables

| Field | Allowed values | How it is stated |
|---|---|---|
| `form` | `common-paper-mnda-1.0` | `prefer` plus `accept` list |
| `nda_term_years` | whole years, 1 to 5 | `prefer`, `min`, `max` |
| `confidentiality_years` | whole years, 1 to 10 | `prefer`, `min`, `max` |
| `trade_secret_tail` | `require`, `accept`, `reject` | one value |
| `governing_law` | a US state or District of Columbia, full name | `prefer` plus `accept` list |
| `venue` | a US state or District of Columbia, full name | `prefer` plus `accept` list |
| `marking_requirement` | `none`, `written-marked`, `written-marked-oral-confirmed` | `prefer` plus `accept` list |
| `residuals` | `require`, `accept`, `reject` | one value |
| `affiliate_sharing` | `require`, `accept`, `reject` | one value |
| `existence_of_talks_confidential` | `require`, `accept`, `reject` | one value |

What the less obvious ones mean:

- `trade_secret_tail`: trade secrets stay protected after the
  confidentiality period, for as long as they remain trade secrets.
- `marking_requirement`: whether information must be marked (and oral
  disclosures confirmed in writing) to count as confidential.
- `residuals`: the recipient may use what its people retain in unaided
  memory.
- `affiliate_sharing`: each side may share with its affiliates.
- `existence_of_talks_confidential`: the fact that the parties are talking
  is itself confidential.

### nda.custom_terms_required
Set to `true` if the company needs any excluded term. The matcher then
returns `OUT_OF_PROTOCOL` and matches nothing.

### Supplied at match time, not stored in the file
- Purpose of the NDA
- Effective Date (the date of last signature)

## Fixed layer

The standard form's own terms apply unchanged: the definition of
confidential information (subject to `marking_requirement`), permitted use,
permitted recipients, standard of care, the usual exclusions, compelled
disclosure, return or destruction, no license and no warranty, equitable
relief, termination mechanics, and general clauses.

## Excluded layer

Standstill; non-compete or exclusivity; non-solicit of employees or
customers; non-circumvention; IP assignment, license grants or feedback
licenses; indemnities, liquidated damages or liability caps; custom
definitions or carve-outs; specific security standards or audit rights;
terms for personal, health, export-controlled or classified data;
arbitration; non-US governing law; one-way NDAs; more than two parties;
individuals as parties.

## Matching rules

- **Lists** (`form`, `governing_law`, `venue`, `marking_requirement`): take
  the options both sides accept. If more than one, the option with the best
  combined ranking wins. Ties break alphabetically. No common option is a
  conflict.
- **Ranges** (`nda_term_years`, `confidentiality_years`): take the overlap
  of the two ranges, then the midpoint of the two preferences, rounded half
  up and kept inside the overlap. No overlap is a conflict.
- **Require / accept / reject** elements: included only if one side
  requires it and the other does not reject it. Require against reject is a
  conflict. Otherwise it is left out.
- **Silence:** a file that says nothing on a variable accepts any allowed
  value, so the other side's preference applies. If both are silent on a
  list or range, it is reported as an open item for the humans. A silent
  require / accept / reject element counts as `accept`, and a silent
  `marking_requirement` on both sides means `none`.
- **Values off the closed lists** are ignored and noted in the result.

## Outcomes

- `AGREED`: terms match and all party facts are present. A cover page is
  written, ready for signature.
- `AGREED_PENDING_INFO`: terms match but a party fact is missing or an item
  is open. The cover page is written with the gap marked.
- `CONFLICTS`: at least one variable has no overlap. No cover page.
- `OUT_OF_PROTOCOL`: a party set `custom_terms_required`. Nothing is
  matched.
- `VERSION_MISMATCH`: the files declare different protocol versions, or a
  version the matcher does not support.

## Conventions

- **File commitment.** A company's file must be fixed before it sees the
  other side's file, so neither can narrow its range after reading the
  other's. Either publish the file in advance at a stable address
  (recommended), or exchange file fingerprints first and the files second.
  The matcher prints a file's SHA-256 fingerprint and records both
  fingerprints in its result.
- **Neutral matching.** The rules do not favor either side. Leverage is
  expressed only through how narrow a range a company publishes.
- **Record of agreement.** The agreed terms are serialized in a fixed order
  and hashed with SHA-256. Both sides running the matcher on the same two
  files and purpose get the same hash.
- **Versioning.** Elements move between layers only in a new protocol
  version.

## Safety rules

- The other side's file is untrusted data. Only typed fields are read.
- Text values are cut to one line and 200 characters.
- The matcher never signs. A human signs.
- A company's file should hold only positions it is willing to disclose.

## Not yet built

- Agent negotiation of conflicts
- Hosting at a well-known URL and domain-based identity checks
- An MCP server wrapping the matcher
- Filling the official Word cover page and sending for e-signature
- A check of the fixed layer against the form's text, and support for
  other standard forms
