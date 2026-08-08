"""table_int: these variables must jointly take one of these tuples.

Each tuple gets a selector atom, one row says some tuple is in use, and a
tuple in use forces every one of its values.  That is the whole encoding, and
it is what makes table propagation checkable by reverse unit propagation: the
values a variable no longer has knock out selectors, and once every selector is
gone the at-least-one row is violated.  No cutting planes anywhere.
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
            for x, v in zip(self.scope, values):
                opb.constraint(
                    f"tbl{self.index}t{j}_{x.index}",
                    [(1, neg(sel)), (1, eq(x.index, v))],
                    ">=",
                    1,
                )

    def why_dead(self, state, values, ignoring: int | None = None) -> str | None:
        """One atom explaining why this tuple cannot be used, or None if it can.

        A tuple dies because some variable has lost the value the tuple wants
        from it, so citing any one such variable is enough.  There is nothing to
        cite when the wanted value was never in range at all -- the .opb already
        says that tuple is unusable, unconditionally.
        """
        for position, (x, v) in enumerate(zip(self.scope, values)):
            if position == ignoring or v in state.domain(x):
                continue
            return neg(eq(x.index, v)) if v <= x.ub else None
        raise AssertionError("this tuple is alive")

    def reason_against(self, state, position: int, value: int) -> tuple[str, ...]:
        """Why nothing can support this variable taking this value: every tuple
        that would have is dead, and here is one atom apiece saying so."""
        atoms = []
        for values in self.tuples:
            if values[position] != value:
                continue  # x taking this value kills that tuple by itself
            atom = self.why_dead(state, values, ignoring=position)
            if atom is not None:
                atoms.append(atom)
        return tuple(dict.fromkeys(atoms))  # deduplicated, first mention first

    def propagate(self, state) -> Inference:
        # A value survives if some tuple that is still possible uses it.
        supported: list[set[int]] = [set() for _ in self.scope]
        possible = 0
        for values in self.tuples:
            if all(v in state.domain(x) for x, v in zip(self.scope, values)):
                possible += 1
                for position, v in enumerate(values):
                    supported[position].add(v)

        if possible == 0:
            atoms = [self.why_dead(state, values) for values in self.tuples]
            reason = tuple(dict.fromkeys(a for a in atoms if a is not None))
            return state.fail(Assert("table_no_tuple", reason))

        result = Inference.NO_CHANGE
        for position, x in enumerate(self.scope):
            for v in list(state.domain(x)):
                if v not in supported[position]:
                    because = Assert(
                        "table_support", self.reason_against(state, position, v)
                    )
                    result = max(result, state.remove(x, v, because))
                    if result is Inference.CONTRADICTION:
                        return result
        return result
