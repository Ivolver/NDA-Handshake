#!/usr/bin/env python3
"""Check a matcher against the published expected results.

Runs every case in examples/expected-results.json and compares the outcome.
Anyone building another implementation of the protocol can feed it the same
example files and compare its results with the same list.

If the `jsonschema` package is installed, also validates every example
file's YAML block against schema/nda-handshake.schema.json and every
case's result against schema/result.schema.json. The schema checks are
optional; without `jsonschema`, this script prints one skip line and
otherwise behaves the same.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))

try:
    import jsonschema

    _NDA_SCHEMA = json.load(open(
        os.path.join(HERE, "schema", "nda-handshake.schema.json"), encoding="utf-8"))
    _RESULT_SCHEMA = json.load(open(
        os.path.join(HERE, "schema", "result.schema.json"), encoding="utf-8"))
    _SCHEMAS = True
except ImportError:
    _SCHEMAS = False


def _yaml_block(path):
    """Return the parsed YAML block at the top of an nda-handshake.md file."""
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    return yaml.safe_load(m.group(1))


def _run_match(files, purpose):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [sys.executable, os.path.join(HERE, "match.py"), *files,
             "--purpose", purpose, "--out", tmp],
            capture_output=True, text=True,
        )
        with open(os.path.join(tmp, "result.json"), encoding="utf-8") as f:
            return json.load(f)


def main():
    with open(os.path.join(HERE, "examples", "expected-results.json"), encoding="utf-8") as f:
        expected = json.load(f)
    failures = 0
    results = {}

    for case in expected["match_cases"]:
        files = [os.path.join(HERE, "examples", name) for name in case["files"]]
        got = _run_match(files, expected["purpose"])
        results[case["name"]] = got
        problems = []
        if got["status"] != case["status"]:
            problems.append(f"status {got['status']}, expected {case['status']}")
        if "terms_hash" in case and got.get("terms_hash") != case["terms_hash"]:
            problems.append("terms hash differs")
        for key in ("governing_law", "venue"):
            if key in case and got.get("terms", {}).get(key) != case[key]:
                problems.append(f"{key} {got.get('terms', {}).get(key)}, expected {case[key]}")
        if "conflicts" in case:
            got_names = sorted(c.split(":")[0] for c in got.get("conflicts", []))
            if got_names != sorted(case["conflicts"]):
                problems.append(f"conflicts {got_names}, expected {sorted(case['conflicts'])}")
        failures += bool(problems)
        print(f"{'FAIL' if problems else 'ok  '}  {case['name']}"
              + (": " + "; ".join(problems) if problems else ""))

    for name, want in expected["fingerprints"].items():
        out = subprocess.run(
            [sys.executable, os.path.join(HERE, "match.py"), "--fingerprint",
             os.path.join(HERE, "examples", name)],
            capture_output=True, text=True,
        ).stdout.strip()
        ok = out == want
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  fingerprint of {name}")

    if not _SCHEMAS:
        print("skip  schema checks (install jsonschema to enable)")
    else:
        for name in sorted(expected["fingerprints"]):
            path = os.path.join(HERE, "examples", name)
            try:
                jsonschema.validate(_yaml_block(path), _NDA_SCHEMA)
                print(f"ok    schema: {name}")
            except jsonschema.ValidationError as e:
                print(f"FAIL  schema: {name}: {e.message}")
                failures += 1
        for case in expected["match_cases"]:
            try:
                jsonschema.validate(results[case["name"]], _RESULT_SCHEMA)
                print(f"ok    schema result: {case['name']}")
            except jsonschema.ValidationError as e:
                print(f"FAIL  schema result: {case['name']}: {e.message}")
                failures += 1

    print("All checks passed." if not failures else f"{failures} check(s) failed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
