#!/usr/bin/env python3
"""Turn a .mzn model into the .fzn.json kindling reads.

Developer tooling.  The generated files are committed, so nobody doing the
practical needs MiniZinc installed, or a working network to install it.

Run it as:  python3 tools/mzn2fzn.py instances/*.mzn

This is only for shipping the .fzn.json files.  If MiniZinc is installed you do
not need it at all -- kindling is a MiniZinc solver, so

    minizinc --solver minizinc/kindling.msc instances/pigeonhole.mzn

runs the whole thing, and --prove <basename> writes the proof as well.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

def flatten(model: pathlib.Path) -> dict:
    result = subprocess.run(
        [
            "minizinc",
            "-c",
            "--solver",
            str(pathlib.Path(__file__).resolve().parent.parent / "minizinc" / "kindling.msc"),
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
