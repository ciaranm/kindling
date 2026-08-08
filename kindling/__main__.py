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


def cycle(n: int = 3) -> Model:
    """x1 < x2 < ... < xn < x1.  Every constraint has a negative coefficient in
    it, which is the case whose justification runs the other way round."""
    model = Model()
    scope = [model.add_variable(n - 1, f"x{i}") for i in range(n)]
    for i in range(n):
        a, b = scope[i], scope[(i + 1) % n]
        model.add_constraint(IntLinLe([1, -1], [a, b], -1))
    return model


def tight_sum() -> Model:
    """Three variables with room to move, a sum that leaves them little of it,
    and bounds that arrive from elsewhere rather than from a decision.

    This one exists to make int_lin_le's justification earn its keep.  When a
    bound comes from a decision the variable is pinned to one value, its bits
    are pinned with it, and the checker can finish the inference by unit
    propagation without being shown any cutting planes at all.  Here the bounds
    come from other constraints and the domains are wide, so no individual bit
    is determined and the derivation is the only way through.
    """
    model = Model()
    a, b, c = (model.add_variable(7, n) for n in "abc")
    model.add_constraint(IntLinLe([1, 1, 1], [a, b, c], 9))
    model.add_constraint(IntLinLe([-1], [b], -3))
    model.add_constraint(IntLinLe([-1], [c], -3))
    model.add_constraint(IntLinLe([-1], [a], -4))
    return model


def over_budget() -> Model:
    """Three tasks that each need at least two, sharing a budget of at most
    five.

    Like tight-sum this exists so that a justification has to be right rather
    than merely present, but for the other sign.  The budget enters the sum
    with a negative coefficient, so the row that cancels its bits is the one
    running the other way, and an int_lin_le that reached for the same
    direction every time is rejected here and nowhere else in the set.
    """
    model = Model()
    a, b, c = (model.add_variable(7, n) for n in "abc")
    budget = model.add_variable(7, "budget")
    model.add_constraint(IntLinLe([1, 1, 1, -1], [a, b, c, budget], 0))
    model.add_constraint(IntLinLe([1], [budget], 5))
    for task in (a, b, c):
        model.add_constraint(IntLinLe([-1], [task], -2))
    return model


def squeeze() -> Model:
    """Three variables sharing two values, and a fourth that is fine.

    This one exists to make all_different's justification earn its keep.  In
    pigeonhole every variable is in the violated set, so the derivation has
    nothing to weaken away and a version that forgot how would still work.
    Here the fourth variable has to be got rid of before the sum comes out.
    """
    model = Model()
    scope = [model.add_variable(1, f"tight{i}") for i in range(3)]
    scope.append(model.add_variable(3, "loose"))
    model.add_constraint(AllDifferentInt(scope))
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
    "cycle": cycle,
    "tight-sum": tight_sum,
    "over-budget": over_budget,
    "squeeze": squeeze,
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
