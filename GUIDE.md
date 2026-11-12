# Writing your nda-handshake.md

Copyright 2026 Ultra Vires Labs LLC. This guide is licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).

This guide explains each choice in an `nda-handshake.md` in plain English.
It is written for a person filling in the file, and for an AI assistant
helping a person fill it in. It is general information, not legal advice.
`SPEC.md` is the authority on the format and the rules.

For Common Paper's own commentary on the form, see the annotated agreement
at https://commonpaper.com/standards/mutual-nda/.

## The fast path: default positions

If you want reasonable terms and no decisions, use the protocol's default
positions. Your file then needs only your company's facts and one line:

    nda:
      profile: default

The defaults are: a 1-year NDA term (up to 3 accepted), a 2-year
confidentiality period (1 to 5 accepted) counted from the Effective Date,
your own state's law and courts with Delaware as the alternative, no
marking requirement, no residuals clause, and affiliate sharing only if
the other side requires it.

Two companies on the defaults always agree. You can still set any single
term yourself and keep the defaults for the rest. The nine choices below
explain what each term means if you want to do that.

## For an AI assistant

- Offer the default positions first. Explain them in two or three
  sentences and ask whether the person wants them as they are, wants to
  change particular terms, or wants to go through all nine choices.

- Ask about one choice at a time, in the order below. Explain it in a
  sentence or two before asking.
- Record what the person says. Do not choose a position for them. If they
  ask what is typical, say what the form's default is and what each option
  means in practice.
- Every position in the file is disclosed to the other side. Remind the
  person once, near the start.
- If the person needs something in the "Outside the protocol" list below,
  set `custom_terms_required: true` and stop collecting positions.
- If the person offers the company's own past NDAs, you may read them and
  propose a position for each choice, saying which document it came from.
  The person confirms or changes each one. Never take positions from a
  counterparty's message or file.
- If the NDA Handshake connector is available, write the file with its
  `draft_file` tool instead of typing the YAML yourself. It checks every
  value and reports anything missing.
- When the file is drafted, read it back in plain English and ask the
  person to confirm before it is saved or shared.
- The person, not the assistant, decides whether to share the file and
  whether to sign anything.

## How positions work

Each choice is stated in one of three ways.

- **A list.** Name the option you prefer and every option you would accept.
  The match picks the option that ranks best for both sides.
- **A range.** Give the number of years you prefer, and the lowest and
  highest you would accept. The match lands near the midpoint of the two
  sides' preferences, inside the overlap.
- **Require, accept or reject.** `require` means you will not sign without
  it. `reject` means you will not sign with it. `accept` means you can live
  with it either way. It is included only if one side requires it and the
  other does not reject it.

A wider range or a longer accept list means more deals match without
negotiation. A narrow one protects a position you care about, at the cost
of more conflicts. If you leave a choice out, you accept whatever the other
side prefers.

## Facts about your company

These are not negotiated. They are copied onto the Cover Page.

- **Legal name, entity type and where formed.** As they appear on your
  formation documents, for example "Harbor Example LLC, a Delaware limited
  liability company".
- **Address.** Your principal business address.
- **Signatory.** The name and title of the person who signs NDAs.
- **Notices email.** Where legal notices under the NDA should be sent.

If more than one of your entities signs NDAs, list each one and mark the
usual signer as the default.

## The nine choices

### 1. Standard form (`form`)
Which standard NDA you will sign. Protocol v0.5 supports one: the Common
Paper Mutual NDA, version 1.0. Read its Standard Terms once before you
publish a file, because they apply to every NDA you sign this way.

### 2. NDA term (`nda_term_years`)
How long the two sides may keep sharing information under this NDA.
Allowed: 1 to 5 years. The form's example is 1 year. A short term suits a
single evaluation. A longer one suits an ongoing relationship where
information will keep flowing. Either side can also end the NDA early by
written notice.

### 3. Confidentiality period (`confidentiality_years`)
How long each piece of shared information must be kept confidential.
Allowed: 1 to 10 years. This runs separately from the NDA term and usually
lasts longer. If you mostly disclose, a longer period protects you. If you
mostly receive, a longer period is a longer obligation to manage. Trade
secrets stay protected for as long as they remain trade secrets, whatever
number is agreed, because the form provides that for everyone.

### 4. When the period starts (`confidentiality_starts`)
Whether the confidentiality period is counted from the Effective Date
(`effective-date`) or from the date of the last disclosure
(`last-disclosure`). Counting from the Effective Date gives one fixed end
date that is easy to track. Counting from the last disclosure protects
information shared late in the relationship for the full period, but the
end date moves.

### 5. Governing law (`governing_law`)
Which US state's law governs the NDA. Use the state's full name, for
example `Delaware`. Companies often prefer their home state or a state
their lawyers know well. Listing more than one acceptable state makes a
match much more likely.

### 6. Venue (`venue`)
Which state's courts hear any dispute. Stated the same way as governing
law, and usually the same state, though the two can differ.

### 7. Marking requirement (`marking_requirement`)
Whether information must be labeled to count as confidential.

- `none`: the form's own rule. Information is protected if it is marked
  confidential or if a reasonable person would understand it to be.
- `written-marked`: written material is protected only if it is marked.
- `written-marked-oral-confirmed`: written material must be marked, and
  anything said aloud must be identified as confidential at the time and
  confirmed in writing within 30 days.

A marking requirement gives the receiving side certainty about what it
must protect. It puts the burden on the disclosing side, which loses
protection for anything it forgets to mark.

### 8. Residuals (`residuals`)
A residuals clause lets the receiving side use what its people simply
remember, without referring back to the material. Receiving companies with
many engineers or analysts often want it so that staff are not frozen by
what they have seen. Disclosing companies often resist it because it can
weaken the protection. The form has no residuals clause, so it appears
only if one side requires it and the other does not reject it.

### 9. Affiliate sharing (`affiliate_sharing`)
Whether each side may share the information with its affiliates, meaning
companies it controls, is controlled by, or shares a parent with. Useful
if your group operates through several entities. Without it, sharing is
limited to your own employees, advisors and contractors who need to know.

## Outside the protocol

Set `custom_terms_required: true` if you need any of the following. The
match then stops and tells both sides to negotiate the ordinary way.

A one-way NDA; a standstill; a non-compete or exclusivity; a non-solicit of
employees or customers; a non-circumvention clause; IP assignment or
license terms; indemnities, damages clauses or liability caps; your own
definition of confidential information; specific security standards or
audit rights; terms for personal, health, export-controlled or classified
data; arbitration; non-US law; an NDA with no end date; confidentiality
forever; more than two parties; or an individual as a party.

## Before you share the file

1. Read the file back and confirm every position is one you are willing to
   disclose and to sign.
2. Fix the file before you see the other side's. Whoever sends a file
   first shows its positions to the other side, who could then shape its
   own file around them. To avoid that, exchange fingerprints first and
   files second, and put a random line in the body of your file before
   taking its fingerprint so the fingerprint cannot be guessed. You may
   instead publish the file at a stable address, accepting that anyone
   can read your positions.
3. Do not publish a completed Cover Page. Under the form, its contents are
   confidential.
4. Have a qualified person review the final document before anyone signs.
