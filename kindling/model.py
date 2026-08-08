"""What a problem looks like before anything happens to it.

Variables are integers with domain [0, ub] -- non-negative, so the bits are
unsigned and no atom name ever needs a minus sign in it.  They are numbered
from 1, and the proof calls variable i "x{i}" regardless of what the model
called it.  The modeller's name survives only in comments.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Variable:
    index: int  # 1-based; the proof calls this x{index}
    ub: int  # domain is [0, ub]
    name: str  # what the model called it, for comments only

    def __post_init__(self):
        if self.ub < 0:
            raise ValueError(f"{self.name}: kindling has no negative domains")


class Constraint:
    """Base class.  Each subclass lives in its own file under constraints/ and
    holds everything about that constraint: how it is written into the OPB
    file, how it propagates, and how it justifies what it propagates."""

    index: int  # 1-based, assigned by Model.add_constraint

    def variables(self) -> list[int]:
        """The variable indices this constraint talks about."""
        raise NotImplementedError

    def define_proof_model(self, opb, model: Model) -> None:
        """Write the rows that say what this constraint means."""
        raise NotImplementedError


@dataclass
class Model:
    variables: list[Variable] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)

    def add_variable(self, ub: int, name: str = "") -> int:
        index = len(self.variables) + 1
        self.variables.append(Variable(index, ub, name or f"x{index}"))
        return index

    def add_constraint(self, constraint: Constraint) -> Constraint:
        constraint.index = len(self.constraints) + 1
        for i in constraint.variables():
            if not 1 <= i <= len(self.variables):
                raise ValueError(f"constraint refers to unknown variable x{i}")
        self.constraints.append(constraint)
        return constraint

    def variable(self, index: int) -> Variable:
        return self.variables[index - 1]

    def ub(self, index: int) -> int:
        return self.variables[index - 1].ub
