# NDA Handshake (v0.3)

Status: experimental, v0.3.

Two companies exchange `nda-handshake.md` files. A matcher works out the NDA terms
both can accept and drafts the cover page. Humans sign.

See `SPEC.md` for the protocol: the file format, the closed list of
negotiable terms, what is excluded, and the matching rules.

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

To print a file's fingerprint, for exchanging before the files themselves:

    python3 match.py --fingerprint examples/harbor-fictional/nda-handshake.md

## Make the signable document

Once a match returns `AGREED`, turn its result into a Word document
(requires `pip install python-docx`):

    python3 make_cover_page.py out/harbor-lakeside/result.json

This writes `mnda.docx` next to the result. It holds the Common Paper Cover
Page filled in with the agreed terms, the Standard Terms attached for
convenience, and a one-page handshake record that is not part of the
agreement. Any other status produces no document.

## Check an implementation

`examples/expected-results.json` lists each example pair with its expected
status, terms hash and conflicts, plus each example file's fingerprint. To
check this matcher against it:

    python3 check_examples.py

Anyone building another implementation of the protocol can run the same
example files and compare against the same list.

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
