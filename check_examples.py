#!/usr/bin/env python3
"""Check a matcher against the published expected results.

Runs every case in examples/expected-results.json and compares the outcome.
Anyone building another implementation of the protocol can feed it the same
example files and compare its results with the same list.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(HERE, "examples", "expected-results.json"), encoding="utf-8") as f:
        expected = json.load(f)
    failures = 0

    for case in expected["match_cases"]:
        with tempfile.TemporaryDirectory() as tmp:
            files = [os.path.join(HERE, "examples", name) for name in case["files"]]
            subprocess.run([sys.executable, os.path.join(HERE, "match.py"), *files,
                            "--purpose", expected["purpose"], "--out", tmp],
                           capture_output=True, text=True)
            with open(os.path.join(tmp, "result.json"), encoding="utf-8") as f:
                got = json.load(f)
        problems = []
        if got["status"] != case["status"]:
            problems.append(f"status {got['status']}, expected {case['status']}")
        if "terms_hash" in case and got.get("terms_hash") != case["terms_hash"]:
            problems.append("terms hash differs")
        if "conflicts" in case:
            got_names = sorted(c.split(":")[0] for c in got.get("conflicts", []))
            if got_names != sorted(case["conflicts"]):
                problems.append(f"conflicts {got_names}, expected {sorted(case['conflicts'])}")
        failures += bool(problems)
        print(f"{'FAIL' if problems else 'ok  '}  {case['name']}"
              + (": " + "; ".join(problems) if problems else ""))

    for name, want in expected["fingerprints"].items():
        out = subprocess.run([sys.executable, os.path.join(HERE, "match.py"), "--fingerprint",
                              os.path.join(HERE, "examples", name)],
                             capture_output=True, text=True).stdout.strip()
        ok = out == want
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  fingerprint of {name}")

    print("All checks passed." if not failures else f"{failures} check(s) failed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
