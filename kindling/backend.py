"""kindling as a MiniZinc solver.

MiniZinc flattens a model, hands the result over as JSON, and reads solutions
back in a fixed format; minizinc/kindling.msc is what tells it we exist.  So a
student can write a model, run one command, and get an answer and a proof of
it, without ever seeing a .fzn.json or knowing that one happened.

    minizinc --solver minizinc/kindling.msc model.mzn
    minizinc --solver minizinc/kindling.msc --prove out model.mzn
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from . import fzn
from .proof.encoding import define_proof_model
from .proof.log import ProofLog
from .search import solve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fzn-kindling")
    parser.add_argument("model", help="a JSON FlatZinc file")
    parser.add_argument("--prove", default="", metavar="BASENAME")
    # MiniZinc is entitled to pass flags we did not ask for; ignoring them
    # beats falling over in the middle of somebody's model.
    args, _ = parser.parse_known_args(argv)

    document = json.loads(pathlib.Path(args.model).read_text())
    try:
        model = fzn.read(document)
    except fzn.Unsupported as complaint:
        print(f"=====ERROR=====\n{complaint}", file=sys.stdout)
        print(f"{args.model}: {complaint}", file=sys.stderr)
        return 2

    if not args.prove:
        solution = solve(model)
    else:
        stem = pathlib.Path(args.prove)
        stem.with_suffix(".opb").write_text(define_proof_model(model).render())
        with stem.with_suffix(".pbp").open("w") as out:
            solution = solve(model, ProofLog(out))
        print(f"wrote {stem}.opb and {stem}.pbp", file=sys.stderr)

    if solution is None:
        print("=====UNSATISFIABLE=====")
    else:
        print(fzn.output_text(document, solution), end="")
        print("==========")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
