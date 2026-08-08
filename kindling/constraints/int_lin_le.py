"""int_lin_le: sum of +/-1 * x <= rhs.

Coefficients are restricted to +1 and -1.  That is not to make the constraint
easier to write, but to make it easier to *justify*: with unit coefficients
every row in the justification enters the sum with multiplier 1, so the whole
derivation is additions and one saturation, and nothing has to be multiplied.
Supporting a general coefficient is one extra "*" in the pol line.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..justify import Assert
from ..model import Constraint, Variable
from ..proof.names import bits
from ..state import Inference


@dataclass
class IntLinLe(Constraint):
    coefficients: list[int]
    scope: list[Variable]
    rhs: int
    index: int = field(default=0)

    def __post_init__(self):
        if len(self.coefficients) != len(self.scope):
            raise ValueError("int_lin_le: one coefficient per variable")
        for c in self.coefficients:
            if c not in (1, -1):
                raise ValueError(
                    f"int_lin_le: coefficient {c} -- kindling only does +1 and -1, "
                    "and supporting more is one of the exercises"
                )

    def variables(self) -> list[Variable]:
        return list(self.scope)

    def define_proof_model(self, opb) -> None:
        readable = " ".join(
            f"{'-' if c < 0 else '+'} {x}" for c, x in zip(self.coefficients, self.scope)
        ).lstrip("+ ")
        opb.comment(f"{readable} <= {self.rhs}")
        terms = [
            (coefficient * weight, literal)
            for coefficient, x in zip(self.coefficients, self.scope)
            for weight, literal in bits(x.index, x.ub)
        ]
        opb.constraint(f"lin{self.index}", terms, "<=", self.rhs)

    def smallest(self, state, position: int) -> int:
        """The least this term can contribute.  With coefficient +1 that is the
        variable's lower bound, and with -1 it is minus its upper bound."""
        x = self.scope[position]
        if self.coefficients[position] > 0:
            return state.lower_bound(x)
        return -state.upper_bound(x)

    def propagate(self, state) -> Inference:
        smallest = [self.smallest(state, i) for i in range(len(self.scope))]
        total = sum(smallest)

        if total > self.rhs:
            return state.fail(Assert("int_lin_le_failure"))

        result = Inference.NO_CHANGE
        for i, x in enumerate(self.scope):
            # Everything else is at least this much, so this term has at most
            # the rest of the budget to play with.
            budget = self.rhs - (total - smallest[i])
            because = Assert("int_lin_le_bound")
            if self.coefficients[i] > 0:
                result = max(result, state.set_upper_bound(x, budget, because))
            else:
                result = max(result, state.set_lower_bound(x, -budget, because))
            if result is Inference.CONTRADICTION:
                return result
        return result
