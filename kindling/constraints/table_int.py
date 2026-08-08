"""table_int: these variables must jointly take one of these tuples.

Each tuple gets a selector atom, one row says some tuple is in use, and a
tuple in use forces every one of its values.  That is the whole encoding, and
it is what makes table propagation checkable by reverse unit propagation: the
values a variable no longer has knock out selectors, and once every selector is
gone the at-least-one row is violated.  No cutting planes anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..model import Constraint
from ..proof.names import eq, neg, selector


@dataclass
class TableInt(Constraint):
    scope: list[int]  # variable indices
    tuples: list[tuple[int, ...]]
    index: int = field(default=0)

    def __post_init__(self):
        for t in self.tuples:
            if len(t) != len(self.scope):
                raise ValueError(f"table_int: tuple {t} is the wrong length")
        if not self.tuples:
            raise ValueError("table_int: no tuples, which is just a failure")

    def variables(self) -> list[int]:
        return list(self.scope)

    def define_proof_model(self, opb, model) -> None:
        opb.comment(
            f"table({', '.join(f'x{i}' for i in self.scope)}) "
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
            if any(v > model.ub(i) for i, v in zip(self.scope, values)):
                # A value no variable can take.  Rather than dropping the tuple
                # and quietly changing the model, say that it is unusable.
                opb.comment(f"tuple {j} = {values} is outside the domains")
                opb.constraint(f"tbl{self.index}t{j}_dead", [(1, neg(sel))], ">=", 1)
                continue
            for i, v in zip(self.scope, values):
                opb.constraint(
                    f"tbl{self.index}t{j}_{i}", [(1, neg(sel)), (1, eq(i, v))], ">=", 1
                )
