"""int_lin_le: sum of +/-1 * x{i} <= rhs.

Coefficients are restricted to +1 and -1.  That is not to make the constraint
easier to write, but to make it easier to *justify*: with unit coefficients
every row in the justification enters the sum with multiplier 1, so the whole
derivation is additions and one saturation, and nothing has to be multiplied.
Supporting a general coefficient is one extra "*" in the pol line.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..model import Constraint
from ..proof.names import bits


@dataclass
class IntLinLe(Constraint):
    coefficients: list[int]
    scope: list[int]  # variable indices
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

    def variables(self) -> list[int]:
        return list(self.scope)

    def define_proof_model(self, opb, model) -> None:
        readable = " ".join(
            f"{'-' if c < 0 else '+'} x{i}" for c, i in zip(self.coefficients, self.scope)
        ).lstrip("+ ")
        opb.comment(f"{readable} <= {self.rhs}")
        terms = [
            (coefficient * weight, literal)
            for coefficient, i in zip(self.coefficients, self.scope)
            for weight, literal in bits(i, model.ub(i))
        ]
        opb.constraint(f"lin{self.index}", terms, "<=", self.rhs)
