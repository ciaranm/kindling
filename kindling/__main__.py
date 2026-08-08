"""python3 -m kindling <instance> [--prove <name>]

The instances are built in for now; reading them from a file comes later.
With --prove, writes <name>.opb and <name>.pbp, which veripb will check:

    python3 -m kindling pigeonhole --prove /tmp/ph
    veripb /tmp/ph.opb /tmp/ph.pbp
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from .constraints.all_different_int import AllDifferentInt
from .constraints.int_lin_le import IntLinLe
from .constraints.table_int import TableInt
from .model import Model
from .proof.encoding import define_proof_model
from .proof.log import ProofLog
from .search import solve


def pigeonhole(pigeons: int = 4, holes: int = 3) -> Model:
    """More pigeons than holes.  Refuted at the root by one Hall violator, so
    the proof has no search in it at all."""
    model = Model()
    scope = [model.add_variable(holes - 1, f"pigeon{i}") for i in range(pigeons)]
    model.add_constraint(AllDifferentInt(scope))
    return model


def agreement() -> Model:
    """Two variables that a table insists agree and all_different insists
    differ.  Neither propagator sees it at the root; it takes two nodes."""
    model = Model()
    a = model.add_variable(1, "a")
    b = model.add_variable(1, "b")
    model.add_constraint(TableInt([a, b], [(0, 0), (1, 1)]))
    model.add_constraint(AllDifferentInt([a, b]))
    return model


def too_small(n: int = 5) -> Model:
    """n different values from 0..n-1 have to add up to at least 0+1+...+n-1,
    and this says they add up to less."""
    model = Model()
    scope = [model.add_variable(n - 1, f"x{i}") for i in range(n)]
    model.add_constraint(AllDifferentInt(scope))
    model.add_constraint(IntLinLe([1] * n, scope, n * (n - 1) // 2 - 1))
    return model


def latin(n: int = 4) -> Model:
    """A satisfiable one, to show the solver is not just saying no."""
    model = Model()
    cell = {
        (r, c): model.add_variable(n - 1, f"cell[{r},{c}]")
        for r in range(n)
        for c in range(n)
    }
    for i in range(n):
        model.add_constraint(AllDifferentInt([cell[i, c] for c in range(n)]))
        model.add_constraint(AllDifferentInt([cell[r, i] for r in range(n)]))
    return model


INSTANCES = {
    "pigeonhole": pigeonhole,
    "agreement": agreement,
    "too-small": too_small,
    "latin": latin,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kindling")
    parser.add_argument("instance", choices=sorted(INSTANCES))
    parser.add_argument("--prove", metavar="NAME", help="write NAME.opb and NAME.pbp")
    args = parser.parse_args(argv)

    model = INSTANCES[args.instance]()

    if args.prove is None:
        solution = solve(model)
    else:
        stem = pathlib.Path(args.prove)
        stem.with_suffix(".opb").write_text(define_proof_model(model).render())
        with stem.with_suffix(".pbp").open("w") as out:
            log = ProofLog(out)
            solution = solve(model, log)
        print(f"wrote {stem}.opb and {stem}.pbp", file=sys.stderr)
        if log.assertions:
            counts: dict[str, int] = {}
            for name in log.assertions:
                counts[name] = counts.get(name, 0) + 1
            print(
                f"{len(log.assertions)} unjustified inferences: "
                + ", ".join(f"{n} x {k}" for k, n in sorted(counts.items())),
                file=sys.stderr,
            )

    if solution is None:
        print("unsatisfiable")
    else:
        for x, value in solution.items():
            print(f"{x.name} = {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
