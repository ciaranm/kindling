"""table_int: these variables must jointly take one of these tuples.

Each tuple gets a selector literal, one constraint says some tuple is in use,
tuple in use forces every one of its values.  That is the whole encoding, and
it is what makes table propagation checkable by reverse unit propagation: the
values a variable no longer has knock out selectors, and once every selector is
gone the at-least-one constraint is violated.  No cutting planes anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..justify import Assert
from ..model import Constraint, Variable
from ..proof.names import eq, neg, selector
from ..state import Inference


@dataclass
class TableInt(Constraint):
    scope: list[Variable]
    tuples: list[tuple[int, ...]]
    index: int = field(default=0)

    def __post_init__(self):
        for t in self.tuples:
            if len(t) != len(self.scope):
                raise ValueError(f"table_int: tuple {t} is the wrong length")
        if not self.tuples:
            raise ValueError("table_int: no tuples, which is just a failure")

    def variables(self) -> list[Variable]:
        return list(self.scope)

    def define_proof_model(self, opb) -> None:
        opb.comment(
            f"table({', '.join(str(x) for x in self.scope)}) "
            f"with {len(self.tuples)} tuples"
        )
        opb.constraint(
            f"tbl{self.index}_sel",
            [(1, selector(self.index, j)) for j in range(len(self.tuples))],
            ">=",
            1,
        )
        for j, values in enumerate(self.tuples):
            sel = selector(self.index, j)
            if any(v > x.ub for x, v in zip(self.scope, values)):
                # A value no variable can take.  Rather than dropping the tuple
                # and quietly changing the model, say that it is unusable.
                opb.comment(f"tuple {j} = {values} is outside the domains")
                opb.constraint(f"tbl{self.index}t{j}_dead", [(1, neg(sel))], ">=", 1)
                continue
            # Using this tuple means every variable takes its value from it,
            # which is a conjunction, which is a constraint asking for all of
            # them at once.
            opb.reified(
                [f"tbl{self.index}t{j}"],
                sel,
                "==>",
                [(1, eq(x.index, v)) for x, v in zip(self.scope, values)],
                len(self.scope),
            )

    def supports(self, state) -> tuple[list[set[int]], int]:
        """Which values each variable could still take, and how many tuples are
        still available.  A value survives if some tuple that is still possible
        uses it."""
        supported: list[set[int]] = [set() for _ in self.scope]
        possible = 0
        for values in self.tuples:
            if all(v in state.domain(x) for x, v in zip(self.scope, values)):
                possible += 1
                for position, v in enumerate(values):
                    supported[position].add(v)
        return supported, possible

    def propagate(self, state) -> Inference:
        supported, possible = self.supports(state)

        if possible == 0:
            # EXERCISE 1.  Both of the Assert(...) in this method say "trust
            # me" rather than giving the checker anything to check.  They can
            # both be Rup(), because this constraint's reasoning really is
            # reverse unit propagation -- see docs/practical.md.
            return state.fail(
                Assert(
                    "table_no_tuple",
                    f"c{self.index}: none of its {len(self.tuples)} tuples is left",
                )
            )

        result = Inference.NO_CHANGE
        for position, x in enumerate(self.scope):
            for v in list(state.domain(x)):
                if v not in supported[position]:
                    # Which table, and which value of which variable: the line
                    # itself says neither, and with two tables over the same
                    # pair of variables there is nothing else to tell them
                    # apart.
                    because = Assert(
                        "table_support",
                        f"c{self.index}: {x} = {v} is in no tuple that is left",
                    )
                    result = max(result, state.remove(x, v, because))
                    if result is Inference.CONTRADICTION:
                        return result
        return result
