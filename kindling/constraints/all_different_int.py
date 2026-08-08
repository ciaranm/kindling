"""all_different_int: no two of these variables take the same value.

This one only ever fails -- it never removes a value.  That is a deliberate
weakness.  A propagator that detects a violated Hall set is enough to make the
search correct, because a complete assignment with a repeat is always a Hall
violation, and it keeps the interesting part of the constraint down to one
argument that a proof can be written about.

Written in the variable-value form -- one at-most-one row per value -- rather
than the more compact form a serious solver would use.  This encoding is what
makes the Hall violator argument come out as a plain sum of rows, and being
able to read that argument off the .opb is worth more here than being small.

A value only one variable can take still gets its row.  It says nothing on its
own, but the Hall violator derivation adds up the rows for every value in the
violated set, and a missing row would leave the sum short.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..justify import Assert, Rup
from ..model import Constraint, Variable
from ..proof.names import eq
from ..state import Inference


@dataclass
class AllDifferentInt(Constraint):
    scope: list[Variable]
    index: int = field(default=0)

    def variables(self) -> list[Variable]:
        return list(self.scope)

    def values(self) -> range:
        """Every value any of these variables could ever take."""
        return range(0, max(x.ub for x in self.scope) + 1)

    def define_proof_model(self, opb) -> None:
        opb.comment(f"all_different({', '.join(str(x) for x in self.scope)})")
        for v in self.values():
            takers = [x for x in self.scope if v <= x.ub]
            opb.constraint(
                f"amo{self.index}_{v}", [(1, eq(x.index, v)) for x in takers], "<=", 1
            )

    def hall_violator(self, state) -> tuple[list[Variable], list[int]] | None:
        """A set of variables with fewer values between them than there are
        variables, or None if there is no such set.

        Found by matching variables to values.  If some variable cannot be
        matched, then the values reachable from it by alternating paths are all
        taken, and those values together with the variables holding them plus
        the unmatchable one are exactly a set that will not fit.
        """
        taken: dict[int, int] = {}  # value -> position in scope holding it

        def match(position: int, reached: set[int]) -> bool:
            for v in state.domain(self.scope[position]):
                if v in reached:
                    continue
                reached.add(v)
                if v not in taken or match(taken[v], reached):
                    taken[v] = position
                    return True
            return False

        for position in range(len(self.scope)):
            reached: set[int] = set()
            if not match(position, reached):
                values = sorted(reached)
                variables = [self.scope[position]] + [
                    self.scope[taken[v]] for v in values
                ]
                # Index order rather than the order the search happened to
                # find them in, so that proofs read left to right and two runs
                # produce the same file.
                return sorted(variables, key=lambda x: x.index), values
        return None

    def hall_steps(self, variables, values) -> tuple[str, ...]:
        """EXERCISE 3.  Cutting planes for "these variables will not fit in
        these values".

        The rows available are @amo{c}_{v}, one per value, each saying at most
        one of these variables takes that value; and @atleast{i}, one per
        variable, saying it takes at least one value.  Add up the right ones
        and see what cancels.  See docs/practical.md.
        """
        raise NotImplementedError("exercise 3")

    def propagate(self, state) -> Inference:
        violator = self.hall_violator(state)
        if violator is None:
            return Inference.NO_CHANGE
        variables, values = violator
        if not values:
            # A variable with nothing left at all.  There is no set of values to
            # argue about, and the node's own line already sees the problem.
            return state.fail(Rup())
        del variables  # until exercise 3 is done
        return state.fail(Assert("all_different_hall"))
