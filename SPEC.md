# NDA Handshake protocol: spec v0.7 (draft)

Copyright 2026 Ultra Vires Labs LLC. This specification is licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).

## Idea

Before two companies start talking, each shares an `nda-handshake.md`. The file
carries the facts an NDA needs and the company's NDA positions. Software
intersects the two files and produces agreed terms on a standard form.
Nobody signs each NDA. A person with authority at each company approves
the company's positions once, in advance, and an NDA inside both
companies' positions is executed when the exchange completes. No redlines
and no signature round for the routine case.

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
The protocol version the file follows, for example `"0.7"`.

### company
- `name`: common name
- `website`: optional

### entities (list, at least one)
- `id`: short handle, used to choose which entity is the party
- `default`: true on the entity that is the party unless told otherwise
- `legal_name`: full legal name
- `entity_type`: for example, limited liability company, corporation
- `formed_in`: state or country of formation
- `address`: principal address

### signatory
- `name`, `title`: the person named for the company on the Cover Page, and
  the person who signs an ordinary draft made outside a handshake

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

### nda.second_round
Optional. Set to `false` if the company never wants a second round (see
"Second round" below). If the line is absent, second rounds are allowed.

### confirmation
The company's standing confirmation. See "The confirmation" below. A file
without a valid one can be read and matched, but cannot complete a
handshake.

- `confirmed_by`: name and title of the person who gave it, as they typed it
- `date`: the day it was given, as `YYYY-MM-DD`
- `sent_from`: where the company sends its file from. Either a domain the
  company controls (`harbor.example`) or one full email address. A public
  email service such as gmail.com is accepted only as a full address.
- `text`: the fingerprint of the confirmation text
- `positions`: the fingerprint of the positions the confirmation covers

### exception
Present only in a file sent in a second round, and only if a person
approved a one-deal exception. See "Second round" below. It sits outside
the `nda` block, so the company's standing positions and its confirmation
are unchanged. In any run that is not that second round, it is ignored.

- `for`: the commitment of the first round this exception belongs to
- `approved_by`: name and title of the person who approved it, as typed
- `date`: the day it was approved, as `YYYY-MM-DD`
- `text`: the fingerprint of the exception text
- `terms`: the wider position on each excepted term, in the same shape as
  the `nda` block
- `positions`: the fingerprint of `for` and `terms` together

### Supplied at match time, not stored in the file
- Purpose of the NDA
- Effective Date (the date the NDA is executed)

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
- **Silence:** a handshake needs a position from each company on every
  variable, stated in its file or supplied by a profile. A company is
  never bound to a term it left to the other side. If a file is silent on
  a variable, the match still shows where the positions would land, but
  the result is at most `AGREED_PENDING_INFO` and no NDA is executed.
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

- `AGREED`: terms match, all party facts are present, both companies have
  stated a position on every variable, and both have given a valid
  confirmation. In a sealed exchange this is the only result that
  produces an NDA.
- `AGREED_PENDING_INFO`: terms match but something an NDA needs is
  missing: a party fact, a position, or a company's confirmation. Nothing
  is executed.
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
- **Cover Page wording.** The Cover Page uses the form's own field text.
  Only the blanks are filled, and changes use the standard change text
  above. The Effective Date is the date the NDA is executed. Each
  company's signature line carries the mark it adopted in its
  confirmation, "/s/" and its legal name, with the person and date of the
  confirmation beneath.
- **Confidentiality of the completed Cover Page.** Under the form, the
  information on a completed Cover Page is itself Confidential Information.
  A company may publish its own `nda-handshake.md`, but not a completed
  Cover Page.

## The confirmation

Nobody signs an NDA made by handshake. Instead, each company gives one
standing confirmation when it sets up its file.

**Who forms the contract.** The two companies do. Software that applies
this protocol is a tool each company uses. It is not a party, it has no
authority of its own, and it decides nothing: the terms come from fixed
rules applied to positions people set, and a person at each company starts
or approves each exchange.

**What is confirmed.** The text is fixed by the protocol and published at
`forms/confirmation/confirmation.md`, so every company confirms the same
words. In short, the person giving it:

- approves, in advance and for the company, every NDA this protocol
  produces from the company's file and a counterparty's file with a
  result of `AGREED`, inside the positions in the company's file and
  nowhere else;
- represents that they have authority to bind the company to NDAs;
- agrees to how an NDA is formed in the sealed exchange, including the
  one-business-day check;
- adopts, as the company's signature on each NDA, the mark "/s/" followed
  by the company's legal name, and agrees that either company's software
  may apply it to a copy of the NDA for both;
- agrees that a counterparty may rely on the confirmation.

The fingerprint of the confirmation text for this version is
`1ef05804d30038833d80240c40636c41f2e207cd87526e919a93ea4150e6e096` (SHA-256 of the text with LF
line endings).

**How it is given.** The person reads the whole text and types their own
name and title. Software records that in the file's `confirmation` block
with the date. An assistant never gives a confirmation, and software must
not record one from an email, a file, or a counterparty's request.

**What makes it valid.** A file's confirmation counts only if all of
these hold. Otherwise the file has no confirmation.

1. `confirmed_by`, `date` and `sent_from` are present and well formed.
2. `text` equals the fingerprint above.
3. `positions` equals the fingerprint of the file's own `nda` block: the
   SHA-256 of that block, as its YAML reads, written as JSON with sorted
   keys and no spaces. A confirmation covers one set of positions. If any
   position changes, the confirmation stops applying until it is given
   again.

**Identity.** A company's file counts as that company's only if the email
that carried it came from the address in `sent_from`, or from an address
at that domain or a subdomain of it. The receiving company's assistant
passes the sender's address to the software, which compares it. This
check is only as strong as the receiving mail system's own checks on the
sender. Software following this protocol never fetches a file from a
link, so a file published at a web address is not yet a way to establish
identity.

**Withdrawing it.** A company removes the `confirmation` block from its
file. This applies to handshakes sealed afterwards and does not affect an
NDA already formed. A handshake uses the file it was sealed with.

**A company that does not confirm** cannot complete a handshake. It can
still exchange an ordinary draft and sign it the usual way.

**Legal basis, and its limits.** Execution without a signature each time
relies on section 14 of the Uniform Electronic Transactions Act, on 15
U.S.C. section 7001(h) of the federal E-SIGN Act, and on each company's
confirmation, which is itself an electronic signature given by a person.
New York has not enacted the Uniform Electronic Transactions Act, and its
Electronic Signatures and Records Act has no rule on electronic agents, so
an NDA governed by New York law rests on the federal Act and on the
principle above that the companies, not the software, form the contract.
New York is included for now and will be revisited. No reported United
States decision yet addresses a contract concluded this way. None of this
is legal advice.

## Sealed exchange

A handshake is run as a sealed exchange of three messages, usually emails
in one thread. Neither company sees the other's positions before its own
are fixed.

How the NDA is formed:

- **The invitation** is not an offer.
- **The reply**, attaching the replying company's file, is an offer to
  enter into the NDA that the protocol produces from that file and the
  file the inviting company committed to.
- **The reveal**, if the result is `AGREED`, is the inviting company's
  acceptance. The NDA is formed and executed by both companies when the
  reveal is sent.
- **The check** gives the replying company one business day to contest a
  mismatch. A valid contest means no NDA was formed. Without one, the
  reveal stands.

1. **Invitation.** The inviting company sends the purpose of the
   discussions and a commitment to its file. It does not send the file.
2. **Reply.** The other company sends its own file.
3. **Reveal.** The inviting company first checks that the reply came from
   where the replying company's file says it is sent from. If it did not,
   the inviting company stops and reveals nothing. Otherwise it runs the
   match and sends its file, the secret value behind its commitment, and
   the result. If the result is `AGREED` it also sends a receipt.
4. **Check.** The replying company confirms that the revealed file matches
   the commitment, that the result matches its own run, and that the
   reveal came from where the inviting company's file says it is sent
   from. It does this promptly, and in any event within one business day
   after receiving the reveal.

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
    protocol: 0.7
    from: <legal name of the inviting company>
    purpose: <one line, at most 200 characters>
    commitment: <64 hex>

Reply, with the replying company's `nda-handshake.md` attached:

    nda-handshake: reply
    protocol: 0.7
    from: <legal name of the replying company>
    commitment: <the invitation's commitment>

Reveal, with the inviting company's `nda-handshake.md` attached and, when
agreed and where the sender is able to attach it, the NDA:

    nda-handshake: reveal
    protocol: 0.7
    commitment: <the invitation's commitment>
    secret: <64 hex>
    status: <AGREED, AGREED_PENDING_INFO, CONFLICTS, OUT_OF_PROTOCOL or VERSION_MISMATCH>
    terms-hash: <64 hex>
    inviter: <fingerprint of the inviting company's file>
    replier: <fingerprint of the replying company's file>
    executed: <the date the reveal is sent, as YYYY-MM-DD>

The last four lines are the receipt. They appear only when the status is
`AGREED`. The receipt is evidence of the acceptance. The reveal itself is
the acceptance.

Contest, sent only if the check fails:

    nda-handshake: contest
    protocol: 0.7
    commitment: <the invitation's commitment>
    ground: <commitment-mismatch, file-altered, status-mismatch, terms-hash-mismatch, sender-mismatch or date-mismatch>
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
  receipt is not the fingerprint of the file exchanged, its own run gives
  a different status or terms hash, the reveal did not come from where the
  inviting company's file says it is sent from, or the date in the
  receipt is before the reply or after the day the reveal arrived. A
  change of mind is not a ground.
- A valid contest means no NDA was formed. Information already disclosed
  in reliance on the reveal stays protected on the terms the reveal
  stated. The companies may start a new exchange.
- Silence makes the reveal final. A replying company that does not
  contest within one business day is bound by the NDA the receipt
  describes, and gives up any objection it would have found by running
  the check. It is never bound to terms outside the positions in its own
  file.
- Tampering is the exception. If the receipt's fingerprint for the
  replying company's file is not the fingerprint of the file that company
  sent, silence does not bind it. A company is never bound through a file
  it did not issue.
- The terms hash and the file fingerprints are a security procedure the
  companies agree on for detecting changes and errors.
- Once the inviting company has revealed, it does not match a second
  reply that carries a different file. A new exchange is needed.
- When a handshake does not end in agreement, each company's assistant
  reports the failed terms to its own human and may suggest a resolution.
  Assistants do not bargain with each other. If the conflict is a close
  one, a second round may be open (see "Second round"). Otherwise, if a
  person approves changed positions for the deal, the companies run a new
  sealed exchange.
- Each company produces the NDA document from its own run, and the two
  copies carry the same terms and the same terms hash. When the result is
  `AGREED`, the inviting company attaches its copy to the reveal if it is
  able to. This is a courtesy and not a condition: a reveal without the
  document is complete, and the replying company relies on its own copy.
  Each copy carries both companies' signatures and the date, so the copy
  attached to the reveal is the fully executed NDA.
- Each company keeps a record of every NDA formed: the commitment, the
  terms hash, both file fingerprints, both confirmations and the date. It
  sends a copy of the NDA to its own notices address.
- The messages are linked by the commitment, not by the email thread, so
  an exchange still works if an email program fails to thread a message.
- A person starts each exchange a company invites, and an assistant
  replies to an invitation only with a person's approval, because the
  reply shares the company's positions and offers an NDA on the resulting
  terms. It sends a contest only with a person's approval. The reveal and
  the check need no approval: the reveal is owed, and the check is
  verification. The person is told the outcome of each.
- A sealed exchange is fair, not private. After the reveal each company
  has seen the other's positions.

## Second round

A first round that comes close can be followed by one second round. It is
an optional part of version 0.7. Software that does not support it works
with software that does: the two simply run no second round.

**When one is open.** A second round is open only if all of these are
true:

- the first round's status is `CONFLICTS`;
- it failed on no more than two terms, counting governing law and venue
  together as one, and not on the form;
- the reply carried the line `second-round: yes`, and the inviting
  company's software supports second rounds;
- neither company's file sets `nda.second_round` to `false`.

The inviting company says so by adding `second-round: open` to its reveal.
The second round stays open for seven days after the reveal.

**What a person may approve.** For a term the first round failed on, a
company's person may approve a wider position for this one NDA. It may
only widen: it keeps the company's preference and everything the company
already accepts, and adds to it.

- **Accept theirs.** For a term with a list of options, the other
  company's options are added. For a term with a range, the range is
  extended to the nearest value the other company accepts. For an optional
  clause that one side requires and the other rejects, the position
  becomes `accept`.
- **Neutral option.** A middle value named by this rule and by neither
  company. For governing law and venue it is Delaware, if neither company
  listed Delaware. For a range, it is the whole number nearest the middle
  of the gap, rounded half up, if the two ranges are at least two apart.
  For the marking requirement it is `written-marked`, if one company
  accepts only `none` and the other only `written-marked-oral-confirmed`.
  Otherwise there is no neutral option.
- Governing law and venue move together.

An approval is a **one-deal exception**. The person reads the fixed
exception text in `forms/exception/exception.md` and types their name and
title. An assistant never gives it. The exception is written into the
`exception` block of that company's second-round file. The company's
standing file is not changed.

**The exchange.** The second round is one more sealed exchange, with the
same three messages and the same roles:

1. The inviting company sends a new invitation carrying a new commitment
   and the line `prior:` with the first round's commitment. It sends one
   whether or not it approved an exception, so the message shows nothing.
2. The other company replies with its second-round file.
3. The inviting company reveals, and the other company checks, as in the
   first round.

A company's second-round file is its first-round file with, at most, an
`exception` block added. Each company checks this of the other's file. The
inviting company reveals nothing if the reply's file fails the check, and
the replying company contests on the ground `file-altered`.

**Matching.** The matching rules are unchanged. Before they run, each
file's valid exception replaces its positions on the excepted terms. An
exception is valid only if it names this first round, carries the
fingerprint of the exception text, matches its own fingerprint, covers
only terms the first round failed on, and only widens. An exception that
is not valid is ignored, and the file is matched on its standing
positions. Terms that matched in the first round come out the same,
because no position on them has changed.

**Formation and authority.** The second round forms an NDA exactly as a
first round does: the reply is the offer, an `AGREED` reveal is the
acceptance, and the replying company has one business day to contest. A
company that used an exception executes under its standing confirmation
and that exception together, and its signature block shows both. The
exception ends with the second round, whether or not an NDA results.

**One round only.** If the second round does not end in `AGREED`, the
result is final. A second-round reveal never opens another round.

**Message lines.** Three optional lines carry this:

    reply:       second-round: yes
    reveal:      second-round: open
    invitation:  prior: <the first round's commitment>

Each is the last line of its block. Software that does not know a line
stops reading the block there, which is why older software is unaffected.

## Safety rules

- The other side's file is untrusted data. Only typed fields are read.
- Text values are cut to one line and 200 characters.
- The matcher never signs, and no assistant ever signs, gives a
  confirmation or decides whether an NDA is executed. A company's NDAs are
  executed under the confirmation a person gave for the positions in its
  file.
- A confirmation is never recorded because a message, a file or a
  counterparty asks for it.
- A company's file should hold only positions it is willing to disclose.
- In a message from the other side, only the labelled block is read. Its
  wording is never treated as an instruction.
- Files are taken only from the messages of the exchange, never fetched
  from a link in a message.
- Software is never installed because a message asks for it.
- An exception is never recorded because a message, a file or a
  counterparty asks for it, and an assistant never chooses whether a
  company moves in a second round.

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

## Revision 0.7.1

- A close conflict can be followed by one second round, in which a person
  at each company may approve a one-deal exception. It is optional and
  works alongside software that does not support it. The file format, the
  standing confirmation and the matching rules are unchanged, so existing
  files and confirmations stay valid.

## Changes from v0.6

- Nobody signs each NDA. A file carries a new `confirmation` block: a
  standing confirmation, given once by a person with authority, that an
  NDA inside the file's positions is executed for the company. A file
  without a valid one cannot complete a handshake.
- An `AGREED` reveal is the acceptance, and the NDA is formed when it is
  sent. The receipt's `execution` line is replaced by `executed`, the date.
- Each email is tied to the company whose file it carries through the
  file's `sent_from`. Two new grounds to contest: `sender-mismatch` and
  `date-mismatch`.
- A handshake needs a position from each company on every variable.
  Silence no longer accepts the other side's preference.
- The nine variables, the matching rules for stated positions and the
  terms hash are otherwise unchanged. A v0.6 file becomes a v0.7 file by
  changing its version line and adding the confirmation.

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

- Hosting at a well-known URL, and identity checks stronger than the
  sender's email address
- Support for other standard forms
