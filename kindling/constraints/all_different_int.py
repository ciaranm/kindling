"""all_different_int: no two of these variables take the same value.

Written in the variable-value form -- one at-most-one row per value -- rather
than the more compact form a serious solver would use.  This encoding is what
makes the Hall violator argument come out as a plain sum of rows, and being
able to read that argument off the .opb is worth more here than being small.

Note that a value that only one variable can take still gets its row.  It says
nothing on its own, but the Hall violator derivation adds up the rows for every
value in the violated set, and a missing row would leave the sum short.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..model import Constraint
from ..proof.names import eq


@dataclass
class AllDifferentInt(Constraint):
    scope: list[int]  # variable indices
    index: int = field(default=0)

    def variables(self) -> list[int]:
        return list(self.scope)

    def values(self, model) -> range:
        """Every value any of these variables could take."""
        return range(0, max(model.ub(i) for i in self.scope) + 1)

    def define_proof_model(self, opb, model) -> None:
        opb.comment(f"all_different({', '.join(f'x{i}' for i in self.scope)})")
        for v in self.values(model):
            takers = [i for i in self.scope if v <= model.ub(i)]
            opb.constraint(
                f"amo{self.index}_{v}", [(1, eq(i, v)) for i in takers], "<=", 1
            )
