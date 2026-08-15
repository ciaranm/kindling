"""Propagators with things wrong with them, on purpose.

Nothing here is used unless you ask for it with --bug.  The point is to see
what proof logging is actually for: a solver with one of these in it still
looks fine.  It runs, it terminates, it prints an answer, and on most instances
the answer is even right.  The tests pass.  What it cannot do is convince the
checker, and the line the checker stops at says where to look.

Two of these are wrong about the problem and two are wrong about the proof, and
telling those apart from the outside is the skill worth having:

  * A solver that removes a value it should have kept gives a wrong answer, and
    the proof fails because the claim being made is false.
  * A solver that removes the right value but cannot say why gives the *right*
    answer, and the proof fails anyway.  Nothing is broken about the search.
    Everything is broken about the evidence.

The second kind is the one testing will never find for you.
"""

from __future__ import annotations

from .constraints.all_different_int import AllDifferentInt
from .constraints.int_lin_le import IntLinLe
from .constraints.table_int import TableInt


def table_forgets_a_tuple() -> None:
    """Support is worked out from all but the last tuple, so a value whose only
    support is that tuple gets removed even though it was fine."""
    original = TableInt.supports

    def supports(self, state):
        keep = self.tuples
        self.tuples = keep[:-1] or keep
        try:
            return original(self, state)
        finally:
            self.tuples = keep

    TableInt.supports = supports


def all_different_too_eager() -> None:
    """A set of k variables sharing k values is perfectly fine.  This one calls
    it a violation, so it refuses solutions that exist."""
    original = AllDifferentInt.hall_violator

    def hall_violator(self, state):
        found = original(self, state)
        if found is not None:
            return found
        for x in self.scope:
            values = sorted(state.domain(x))
            others = [y for y in self.scope if set(state.domain(y)) <= set(values)]
            if len(others) == len(values) and len(values) < len(self.scope):
                return sorted(others, key=lambda y: y.index), values
        return None

    AllDifferentInt.hall_violator = hall_violator


def linear_off_by_one() -> None:
    """Each term is assumed to be worth one more than it can be, so the budget
    left for everything else is one too small and bounds get over-tightened."""
    original = IntLinLe.smallest
    IntLinLe.smallest = lambda self, state, position: original(self, state, position) + 1


def linear_forgets_a_constraint() -> None:
    """The propagation is right.  The derivation leaves out one of the
    constraints it needs, so the proof cannot be made to support a conclusion
    that is true."""
    def steps(self, bounds, ignoring=None):
        del bounds, ignoring
        return [f"@lin{self.index}"]

    IntLinLe.steps = steps


BUGS = {
    "table-forgets-a-tuple": table_forgets_a_tuple,
    "all-different-too-eager": all_different_too_eager,
    "linear-off-by-one": linear_off_by_one,
    "linear-forgets-a-constraint": linear_forgets_a_constraint,
}


def apply(name: str) -> None:
    BUGS[name]()
