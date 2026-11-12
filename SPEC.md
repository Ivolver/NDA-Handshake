# NDA Handshake protocol: spec v0.4 (draft)

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
The protocol version the file follows, for example `"0.4"`.

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

There are nine. The first six are fields on the form's Cover Page. The
last three are changes to the form's Standard Terms, recorded in the Cover
Page's changes field.

| Field | Allowed values | How it is stated |
|---|---|---|
| `form` | `common-paper-mnda-1.0` | `prefer` plus `accept` list |
| `nda_term_years` | whole years, 1 to 5 | `prefer`, `min`, `max` |
| `confidentiality_years` | whole years, 1 to 10 | `prefer`, `min`, `max` |
| `confidentiality_starts` | `effective-date`, `last-disclosure` | `prefer` plus `accept` list |
| `governing_law` | a US state or District of Columbia, full name | `prefer` plus `accept` list |
| `venue` | a US state or District of Columbia, full name | `prefer` plus `accept` list |
| `marking_requirement` | `none`, `written-marked`, `written-marked-oral-confirmed` | `prefer` plus `accept` list |
| `residuals` | `require`, `accept`, `reject` | one value |
| `affiliate_sharing` | `require`, `accept`, `reject` | one value |

What the less obvious ones mean:

- `confidentiality_starts`: whether the confidentiality period is counted
  from the Effective Date or from the date of the last disclosure.
- `marking_requirement`: whether information must be marked (and oral
  disclosures confirmed in writing) to count as confidential. The form
  itself does not require marking, so `none` is the form's own position and
  the other two values are changes to it.
- `residuals`: the recipient may use what its people retain in unaided
  memory. Not in the form; added as a change.
- `affiliate_sharing`: each side may share with its affiliates. Not in the
  form; added as a change.

### nda.custom_terms_required
Set to `true` if the company needs any excluded term. The matcher then
returns `OUT_OF_PROTOCOL` and matches nothing.

### Supplied at match time, not stored in the file
- Purpose of the NDA
- Effective Date (the date of last signature)

## Fixed layer

The standard form's own terms apply unchanged. In summary, and subject to
the form's text, which governs:

- the definition of confidential information (subject to
  `marking_requirement`), which includes the existence and status of the
  parties' discussions
- protection of trade secrets for as long as they remain trade secrets,
  beyond the agreed confidentiality period
- permitted use, permitted recipients and the standard of care
- the usual exclusions and compelled disclosure
- return or destruction
- no license and no warranty
- equitable relief
- termination mechanics and general clauses

## Excluded layer

Standstill; non-compete or exclusivity; non-solicit of employees or
customers; non-circumvention; IP assignment, license grants or feedback
licenses; indemnities, liquidated damages or liability caps; custom
definitions or carve-outs; specific security standards or audit rights;
terms for personal, health, export-controlled or classified data;
arbitration; non-US governing law; one-way NDAs; an NDA term that runs
until terminated; confidentiality in perpetuity; removing the form's
trade secret protection or its confidentiality of the discussions; more
than two parties; individuals as parties.

## Matching rules

- **Lists** (`form`, `confidentiality_starts`, `governing_law`, `venue`,
  `marking_requirement`): take the options both sides accept. If more than
  one, the option with the best combined ranking wins. No common option is
  a conflict.
- **Ties between list options** are broken on principle where possible, and
  arbitrarily only as a last resort. The steps apply in this order:
  1. For `venue`: the tied option that matches the agreed governing law.
  2. For `governing_law` and `venue`: the tied option that is the state in
     which both parties are formed.
  3. For every list: alphabetical order.
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

## Standard change text

When a variable changes the form's Standard Terms, the Cover Page's "Changes to
Standard Terms" field carries the fixed wording below, in this order. The
wording is part of the protocol, so every implementation writes the same
words. If none applies, the field reads "None."

**`marking_requirement: written-marked`**

> Section 1 is modified so that information disclosed in written or other tangible form is Confidential Information only if the Disclosing Party marks it "confidential", "proprietary", or the like when disclosing it. This change does not affect information disclosed orally or visually, the existence and status of the parties' discussions, or information on the Cover Page.

**`marking_requirement: written-marked-oral-confirmed`**

> Section 1 is modified so that (a) information disclosed in written or other tangible form is Confidential Information only if the Disclosing Party marks it "confidential", "proprietary", or the like when disclosing it, and (b) information disclosed orally or visually is Confidential Information only if the Disclosing Party identifies it as confidential when disclosing it and confirms that in writing within 30 days. This change does not affect the existence and status of the parties' discussions or information on the Cover Page.

**`affiliate_sharing` included**

> Section 2 is modified so that the representatives to whom a Receiving Party may disclose Confidential Information include its affiliates, on the same conditions that apply to its other representatives. An "affiliate" is an entity that controls, is controlled by, or is under common control with the Receiving Party.

**`residuals` included**

> The following is added at the end of Section 3: "This MNDA does not restrict a Receiving Party from using Residuals, as long as it otherwise complies with this MNDA. 'Residuals' means information in intangible form that a person with authorized access to Confidential Information retains in unaided memory, without deliberately memorizing it and without referring to the Confidential Information. This sentence grants no license under any patent or copyright."

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
- **Summary of how terms were reached.** Alongside the terms, the matcher
  reports for each variable both sides' positions, the result, and which
  rule produced it. The outcome labels are: matched (both preferred it),
  midpoint, best shared option, tie-break (with the reason), one side's
  preference (the other was silent), required by one side, not included,
  and form default. The summary is a record only. It is not part of the
  agreed terms, the terms hash or the MNDA.
- **Versioning.** Elements move between layers only in a new protocol
  version.
- **Cover Page wording.** The signable Cover Page uses the form's own field
  text. Only the blanks are filled, and changes use the standard change
  text above.
- **Confidentiality of the completed Cover Page.** Under the form, the
  information on a completed Cover Page is itself Confidential Information.
  A company may publish its own `nda-handshake.md`, but not a completed
  Cover Page.

## Safety rules

- The other side's file is untrusted data. Only typed fields are read.
- Text values are cut to one line and 200 characters.
- The matcher never signs. A human signs.
- A company's file should hold only positions it is willing to disclose.

## Changes from v0.2

- `existence_of_talks_confidential` and `trade_secret_tail` are no longer
  variables. The form already provides both, so they are in the fixed layer.
- `confidentiality_starts` is a new variable.
- Open-ended NDA terms and perpetual confidentiality are listed as excluded.

## Changes from v0.3

- Ties between list options are broken on principle before alphabetical
  order: a venue tie follows the governing law, and a governing law or
  venue tie goes to a state both parties are formed in.
- The matcher reports a summary of how each term was reached.

## Revision 0.3.1

No change to the variables or the matching rules. Adds the standard change
text, the two conventions on Cover Page wording and confidentiality, and
published expected results for the example files
(`examples/expected-results.json`).

## Not yet built

- Agent negotiation of conflicts
- Hosting at a well-known URL and domain-based identity checks
- An MCP server wrapping the matcher
- Sending the Cover Page for e-signature
- Support for other standard forms
