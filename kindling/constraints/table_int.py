"""table_int: these variables must jointly take one of these tuples.

Each tuple gets a selector atom, one constraint says some tuple is in use, and
tuple in use forces every one of its values.  That is the whole encoding, and
it is what makes table propagation checkable by reverse unit propagation: the
values a variable no longer has knock out selectors, and once every selector is
gone the at-least-one constraint is violated.  No cutting planes anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..justify import Rup
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
            for x, v in zip(self.scope, values):
                opb.constraint(
                    f"tbl{self.index}t{j}_{x.index}",
                    [(1, neg(sel)), (1, eq(x.index, v))],
                    ">=",
                    1,
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
            return state.fail(Rup())

        result = Inference.NO_CHANGE
        for position, x in enumerate(self.scope):
            for v in list(state.domain(x)):
                if v not in supported[position]:
                    result = max(result, state.remove(x, v, Rup()))
                    if result is Inference.CONTRADICTION:
                        return result
        return result
