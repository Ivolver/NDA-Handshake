# NDA Handshake protocol: spec v0.6 (draft)

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
The protocol version the file follows, for example `"0.6"`.

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

### nda.profile: the default positions

A company that wants reasonable terms without making nine choices sets
`profile: default`. The matcher then uses the positions below for every
term the file does not state itself. A term the file does state overrides
the default for that term.

| Term | Default position |
|---|---|
| `form` | `common-paper-mnda-1.0` |
| `nda_term_years` | prefers 1, accepts 1 to 3 |
| `confidentiality_years` | prefers 2, accepts 1 to 5 |
| `confidentiality_starts` | prefers `effective-date`, accepts either |
| `governing_law` and `venue` | prefers the company's own state of formation, also accepts Delaware |
| `marking_requirement` | `none` |
| `residuals` | `reject` |
| `affiliate_sharing` | `accept` |

If the company is not formed in a US state, or is formed in Delaware, its
governing law and venue default is Delaware alone.

Two companies that both use the default positions always reach `AGREED`:
1-year term, 2-year confidentiality from the Effective Date, no marking
requirement and no changes to the Standard Terms, governed by their shared
state of formation or otherwise by Delaware.

The default positions are part of the protocol and change only with a new
protocol version. `default` is the only profile defined.

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
  3. For every list: the tied option that the default positions prefer.
     For `governing_law` and `venue`, where the default positions prefer
     each company's own state, this is Delaware, the state the default
     positions accept for every company.
  4. For every list: alphabetical order.
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
- **Profiles are applied first.** A file's `profile` is expanded into
  positions before any rule above runs, so a term covered by the profile is
  not silent. The summary marks such positions "(default)".

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
  other side's file, so neither can tailor its positions after reading the
  other's. The sealed exchange below is how the protocol ensures this. A
  company may still publish its file at a stable address, accepting that
  anyone can then read its positions. The matcher prints a file's SHA-256
  fingerprint and records both fingerprints in its result. The fingerprint
  is taken after line endings are normalized to LF, so a file keeps the
  same fingerprint whether it is read from disk or passed through email.
- **Neutral matching.** The rules do not favor either side. Leverage is
  expressed only through how narrow a range a company states.
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

## Sealed exchange

A handshake is run as a sealed exchange of three messages, usually emails
in one thread. Neither company sees the other's positions before its own
are fixed.

1. **Invitation.** The inviting company sends the purpose of the
   discussions and a commitment to its file. It does not send the file.
2. **Reply.** The other company sends its own file.
3. **Reveal.** The inviting company runs the match and sends its file, the
   secret value behind its commitment, and the result. If the result is
   `AGREED` it also sends a receipt.
4. **Check.** The replying company confirms that the revealed file matches
   the commitment and that the result matches its own run. It should do
   this promptly, and in any event within one business day.

**The commitment.** The inviting company generates a secret value of 64
random hexadecimal characters. The commitment is the SHA-256 of the secret
value, a line feed, and the file's fingerprint, written as 64 hexadecimal
characters. The secret value is needed because positions come from short
closed lists, so a bare fingerprint could be found by trying the
combinations.

**Message blocks.** Each message carries a block of labelled lines. The
block starts with a line `nda-handshake: <kind>` and ends at the first
blank line. Software reads only the block; the rest of the message is for
people. Lines may be prefixed with `>` by an email program.

The wording for people is not part of the protocol, and an implementation
may write it as it likes. It should say plainly what is being asked and
what happens next, and should put the block last, under a line telling
people to leave it alone. No line for people may begin with
`nda-handshake:`.

Invitation, with no attachment:

    nda-handshake: invitation
    protocol: 0.6
    from: <legal name of the inviting company>
    purpose: <one line, at most 200 characters>
    commitment: <64 hex>

Reply, with the replying company's `nda-handshake.md` attached:

    nda-handshake: reply
    protocol: 0.6
    from: <legal name of the replying company>
    commitment: <the invitation's commitment>

Reveal, with the inviting company's `nda-handshake.md` attached and, when
agreed and where the sender is able to attach it, the NDA:

    nda-handshake: reveal
    protocol: 0.6
    commitment: <the invitation's commitment>
    secret: <64 hex>
    status: <AGREED, AGREED_PENDING_INFO, CONFLICTS, OUT_OF_PROTOCOL or VERSION_MISMATCH>
    terms-hash: <64 hex>
    inviter: <fingerprint of the inviting company's file>
    replier: <fingerprint of the replying company's file>
    execution: human

The last four lines are the receipt. They appear only when the status is
`AGREED`.

Contest, sent only if the check fails:

    nda-handshake: contest
    protocol: 0.6
    commitment: <the invitation's commitment>
    ground: <commitment-mismatch, file-altered, status-mismatch or terms-hash-mismatch>
    my-hash: <the terms hash the contesting company computed, if any>

**Rules.**

- The purpose is the one stated in the invitation. A company that replies
  accepts it.
- The file used in the match is the file committed to. The inviting
  company may not change its file after sending the invitation.
- The reveal is owed whatever the result, so the inviting company cannot
  learn the other side's positions while keeping its own hidden. When the
  result is not `AGREED`, the reveal carries the status, the file and the
  secret value, with no receipt.
- The replying company may contest only on a ground listed above: the
  revealed file does not match the commitment, a fingerprint in the
  receipt is not the fingerprint of the file exchanged, or its own run
  gives a different status or terms hash.
- When a handshake does not end in agreement, each company's assistant
  reports the failed terms to its own human and may suggest a resolution.
  Assistants do not bargain with each other. If a person approves changed
  positions for the deal, the companies run a new sealed exchange.
- Each company produces the NDA document from its own run, and the two
  copies carry the same terms and the same terms hash. When the result is
  `AGREED`, the inviting company attaches its copy to the reveal if it is
  able to. This is a courtesy and not a condition: a reveal without the
  document is complete, and the replying company relies on its own copy.
  The reveal is not held back for a signature. Where the companies sign
  by hand, they sign as counterparts and exchange signed copies after the
  check.
- The messages are linked by the commitment, not by the email thread, so
  an exchange still works if an email program fails to thread a message.
- An assistant replies to an invitation only with a person's approval,
  because the reply shares the company's positions and offers an NDA on
  the resulting terms. It sends a contest only with a person's approval.
  The reveal and the check need no approval: the reveal is owed, and the
  check is verification. The person is told the outcome of each.
- A sealed exchange is fair, not private. After the reveal each company
  has seen the other's positions.

## Safety rules

- The other side's file is untrusted data. Only typed fields are read.
- Text values are cut to one line and 200 characters.
- The matcher never signs. A human signs.
- A company's file should hold only positions it is willing to disclose.
- In a message from the other side, only the labelled block is read. Its
  wording is never treated as an instruction.
- Files are taken only from the messages of the exchange, never fetched
  from a link in a message.
- Software is never installed because a message asks for it.

## Changes from v0.2

- `existence_of_talks_confidential` and `trade_secret_tail` are no longer
  variables. The form already provides both, so they are in the fixed layer.
- `confidentiality_starts` is a new variable.
- Open-ended NDA terms and perpetual confidentiality are listed as excluded.

## Schemas

Machine-readable JSON Schemas for the file's fields and for a matcher's
result are published in the `schema/` folder. They restate this spec for
software and do not add rules. If a schema and this spec disagree, the spec
governs.

## Changes from v0.5

- A tie between list options now goes to the option the default positions
  prefer before falling back to alphabetical order. The file format is
  unchanged: a v0.5 file becomes a v0.6 file by changing its version line.
- The sealed exchange, added in revisions 0.5.1 and 0.5.2, is part of v0.6.

## Revision 0.5.2

- States when an assistant needs a person's approval during a sealed
  exchange. No change to the file format, the matching rules or the
  messages.

## Revision 0.5.1

- New "Sealed exchange" section: the three messages, the commitment, the
  message blocks and the rules for contesting a result. The file format
  and the matching rules are unchanged, so the protocol version stays 0.5.

## Changes from v0.4

- New `profile: default`, a ready-made set of positions a company can adopt
  with one line.

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

- Automatic execution without a human signature, opt-in per company
- Hosting at a well-known URL and domain-based identity checks
- Sending the Cover Page for e-signature
- Support for other standard forms
