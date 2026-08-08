#!/usr/bin/env python3
"""Rebuilds the spike .opb files and checks every proof, expected failures too."""

import pathlib
import subprocess
import sys

import build

HERE = pathlib.Path(__file__).parent

# proof file -> what veripb should say about it
EXPECTED = {
    "01-linear/linear.pbp": "VERIFIED",
    "01-linear/linear-rup-only.pbp": "REJECTED",
    "02-linear-neg/linear-neg.pbp": "VERIFIED",
    "02-linear-neg/linear-neg-rup-only.pbp": "REJECTED",
    "03-pigeonhole/pigeonhole.pbp": "VERIFIED",
    "04-table/table.pbp": "VERIFIED",
    "05-search/search.pbp": "VERIFIED",
    "05-search/search-assertions.pbp": "UNDER ASSERTIONS",
}


def outcome(opb, pbp):
    r = subprocess.run(
        ["veripb", str(opb), str(pbp)], capture_output=True, text=True
    )
    text = r.stdout + r.stderr
    if "s UNDER ASSERTIONS" in text:
        return "UNDER ASSERTIONS"
    if "s VERIFIED" in text:
        return "VERIFIED"
    return "REJECTED"


def main():
    for name, text in build.EXAMPLES.items():
        d = HERE / name
        d.mkdir(exist_ok=True)
        (d / f"{name.split('-', 1)[1]}.opb").write_text(text)

    failures = 0
    for rel, want in EXPECTED.items():
        pbp = HERE / rel
        opb = next(pbp.parent.glob("*.opb"))
        got = outcome(opb, pbp)
        ok = got == want
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {rel}: {got}" + ("" if ok else f" (wanted {want})"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
