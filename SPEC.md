# NDA Handshake: company.md spec v0.1 (draft)

Copyright 2026 Ultra Vires Labs LLC. This specification is licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).

## Idea

Before two companies start talking, each shares a `company.md`. The file
carries the facts an NDA needs and the company's NDA positions. Software
intersects the two files and produces agreed terms on a standard form. A
human on each side signs. No redlines for the routine case.

## File layout

A `company.md` has two parts:

1. A YAML block at the top, between `---` lines. This is the only part
   software reads.
2. A markdown body for humans and for general-purpose agents. The matcher
   never reads it.

## Fields

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

### nda
- `form`: standard forms the company will sign (`prefer` plus `accept` list)
- `type`: `mutual` or `one-way` (`prefer` plus `accept` list)
- `nda_term_years`: `prefer`, `min`, `max`
- `confidentiality_years`: `prefer`, `min`, `max`
- `governing_law`: `prefer` plus `accept` list
- `venue`: `prefer` plus `accept` list
- `riders`: each one is `require`, `accept` or `reject`
  - `residuals`
  - `affiliate_sharing`
  - `non_solicit`

The purpose of the NDA is deal-specific, so it is not in the file. A human
supplies it when running the match.

## Matching rules

- Lists (`form`, `type`, `governing_law`, `venue`): take the options both
  sides accept. If more than one, the option with the best combined ranking
  wins. Ties break alphabetically. No common option is a conflict.
- Ranges (`nda_term_years`, `confidentiality_years`): take the overlap of
  the two ranges, then the midpoint of the two preferences, kept inside the
  overlap. No overlap is a conflict.
- Riders: included only if at least one side requires it and the other does
  not reject it. Require against reject is a conflict.

## Outcomes

- `AGREED`: terms match and all party facts are present. A cover page is
  written, ready for signature.
- `AGREED_PENDING_INFO`: terms match but a party fact is missing. The cover
  page is written with the gap marked.
- `CONFLICTS`: at least one term has no overlap. No cover page. Humans (or,
  in a later version, agents with bounded authority) resolve the listed items.

## Record of agreement

The agreed terms are serialized in a fixed order and hashed with SHA-256.
Both sides can run the matcher on the same two files and get the same hash.

## Safety rules

- The other side's file is untrusted data. Only typed fields are read.
- Text values are cut to one line and 200 characters.
- The matcher never signs. A human signs.
- A company's file should hold only positions it is willing to disclose.
  Anything more sensitive belongs in a private playbook, not here.

## Not in v0.1

- Agent negotiation of conflicts
- Hosting at a well-known URL and domain-based identity checks
- An MCP server wrapping the matcher
- Filling the official Word cover page and sending for e-signature
