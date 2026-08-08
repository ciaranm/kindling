#!/usr/bin/env python3
"""Turn a .mzn model into the .fzn.json kindling reads.

Developer tooling.  The generated files are committed, so nobody doing the
practical needs MiniZinc installed, or a working network to install it.

Run it as:  python3 tools/mzn2fzn.py instances/*.mzn

Gecode's library is used because it declares all_different and table as native
rather than decomposing them, which the default library does -- decomposed,
all_different comes out as a pile of int_lin_ne and kindling cannot do that at
all.  Gecode names its table constraint after itself, so that gets renamed on
the way out and the reader never has to know.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

RENAME = {"gecode_table_int": "fzn_table_int"}


def flatten(model: pathlib.Path) -> dict:
    result = subprocess.run(
        [
            "minizinc",
            "-c",
            "--solver",
            "gecode",
            "--fzn-format",
            "json",
            "--output-fzn-to-stdout",
            str(model),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"{model}: minizinc said\n{result.stderr}")
    document = json.loads(result.stdout)
    for constraint in document.get("constraints", []):
        constraint["id"] = RENAME.get(constraint["id"], constraint["id"])
    # The bits we do not read, dropped so that what is committed is what is used.
    document.pop("output", None)
    document.pop("version", None)
    return document


def main(argv: list[str]) -> int:
    if not argv:
        raise SystemExit(__doc__)
    for name in argv:
        model = pathlib.Path(name)
        document = flatten(model)
        out = model.with_suffix(".fzn.json")
        out.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")
        print(
            f"{out}: {len(document.get('variables', {}))} variables, "
            f"{len(document.get('constraints', []))} constraints"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
