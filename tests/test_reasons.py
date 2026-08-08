"""Are the reasons true?

An asserted line is not checked by anyone -- that is what asserting means -- so
a propagator can give a wrong reason and the proof will still come back UNDER
ASSERTIONS with nothing amiss.  The mistake would only surface in stage 4, when
the assertion is replaced by a derivation and the derivation cannot be made to
produce it.  So check them here instead, and by brute force.

Every clause a propagator logs claims to follow from that one constraint, not
from the model as a whole and not from the search.  So the test is: enumerate
every assignment the constraint permits, and demand the clause holds in all of
them.  That catches a reason that cites too little, which is the mistake that
matters -- a reason citing too much is merely wasteful.
"""

import itertools
import random
import re
import unittest

from kindling.constraints.all_different_int import AllDifferentInt
from kindling.constraints.int_lin_le import IntLinLe
from kindling.constraints.table_int import TableInt
from kindling.model import Model
from kindling.proof.log import NoProof, failure_clause, inference_clause
from kindling.state import State
from tests.test_solver import satisfies

ATOM = re.compile(r"^(~?)x(\d+)(eq|ge)(\d+)$")


def atom_holds(atom: str, assignment: dict[int, int]) -> bool:
    """Whether an atom is true when the variables take these values."""
    match = ATOM.match(atom)
    if match is None:
        raise AssertionError(f"unreadable atom {atom!r}")
    negated, index, kind, value = match.groups()
    value = int(value)
    actual = assignment[int(index)]
    holds = actual == value if kind == "eq" else actual >= value
    return not holds if negated else holds


class Recorder(NoProof):
    """Catches what a propagator claims, without writing a proof."""

    def __init__(self):
        self.clauses: list[list[str]] = []

    def infer(self, atom, because):
        self.clauses.append(inference_clause(atom, because))

    def failed(self, because):
        self.clauses.append(failure_clause(because))


def assignments(model: Model):
    for combination in itertools.product(*(range(x.ub + 1) for x in model.variables)):
        yield {x.index: v for x, v in zip(model.variables, combination)}


class ReasonChecker(unittest.TestCase):
    def check(self, model: Model, narrowings) -> int:
        """Narrow some domains, propagate, and demand every clause the
        constraint logged is one the constraint really does imply."""
        constraint = model.constraints[0]
        recorder = Recorder()
        state = State(model, recorder)
        for x, value in narrowings:
            state.domain(x).remove(value)
        if any(state.domain(x).is_empty() for x in model.variables):
            return 0

        constraint.propagate(state)

        for clause in recorder.clauses:
            for assignment in assignments(model):
                by_variable = {
                    x: assignment[x.index] for x in constraint.variables()
                }
                if not satisfies(constraint, by_variable):
                    continue
                self.assertTrue(
                    any(atom_holds(a, assignment) for a in clause),
                    f"{type(constraint).__name__} claimed {clause}, but "
                    f"{assignment} satisfies the constraint and falsifies it",
                )
        return len(recorder.clauses)


class TestReasons(ReasonChecker):
    def random_narrowings(self, rng, model, count):
        return [
            (x, rng.randint(0, x.ub))
            for x in rng.choices(model.variables, k=count)
        ]

    def test_int_lin_le(self):
        rng = random.Random(0)
        claims = 0
        for trial in range(400):
            model = Model()
            scope = [model.add_variable(rng.randint(1, 4)) for _ in range(3)]
            model.add_constraint(
                IntLinLe([rng.choice([1, -1]) for _ in scope], scope, rng.randint(-2, 5))
            )
            with self.subTest(trial=trial):
                claims += self.check(model, self.random_narrowings(rng, model, 3))
        self.assertGreater(claims, 100, "the propagator barely fired")

    def test_table_int(self):
        rng = random.Random(1)
        claims = 0
        for trial in range(400):
            model = Model()
            scope = [model.add_variable(rng.randint(1, 3)) for _ in range(3)]
            tuples = sorted(
                {
                    tuple(rng.randint(0, x.ub) for x in scope)
                    for _ in range(rng.randint(1, 4))
                }
            )
            model.add_constraint(TableInt(scope, tuples))
            with self.subTest(trial=trial):
                claims += self.check(model, self.random_narrowings(rng, model, 2))
        self.assertGreater(claims, 100, "the propagator barely fired")

    def test_all_different_int(self):
        rng = random.Random(2)
        claims = 0
        for trial in range(400):
            model = Model()
            scope = [model.add_variable(rng.randint(1, 3)) for _ in range(3)]
            model.add_constraint(AllDifferentInt(scope))
            with self.subTest(trial=trial):
                claims += self.check(model, self.random_narrowings(rng, model, 3))
        self.assertGreater(claims, 20, "the propagator barely fired")


if __name__ == "__main__":
    unittest.main()
