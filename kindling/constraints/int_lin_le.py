"""int_lin_le: sum of +/-1 * x <= rhs.

Coefficients are restricted to +1 and -1.  That is not to make the constraint
easier to write, but to make it easier to *justify*: with unit coefficients
every constraint in the justification enters the sum with multiplier 1, so the
whole derivation is additions and one saturation, and nothing has to be
multiplied.
Supporting a general coefficient is one extra "*" in the pol line.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..justify import Pol
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

    def channelling(self, position: int, value: int) -> str:
        """The constraint tying one of these variables' bits to one of its order
        atoms.

        Which direction depends only on the sign of the coefficient.  A term
        that counts upwards needs its variable bounded below, and _up is the one
        that says an order atom forces the bits up; a term that counts downwards
        needs the opposite, and that is _dn.  The whole difference between a
        positive and a negative coefficient, in the proof, is these two letters.
        """
        x = self.scope[position]
        return f"@x{x.index}ge{value}_{'up' if self.coefficients[position] > 0 else 'dn'}"

    def bound_values(self, state) -> list[int | None]:
        """For each term, the order atom whose constraint will cancel its bits
        away, or None when the bound is the one it was declared with and there
        is no atom to cite -- those terms just stay in the sum, which costs
        nothing."""
        values: list[int | None] = []
        for i, x in enumerate(self.scope):
            if self.coefficients[i] > 0:
                lower = state.lower_bound(x)
                values.append(lower if lower > 0 else None)
            else:
                upper = state.upper_bound(x)
                values.append(upper + 1 if upper < x.ub else None)
        return values

    def steps(self, bounds, ignoring: int | None = None) -> list[str]:
        """Start from @lin, the PB constraint saying what this int_lin_le means,
        and add one channelling constraint per term, cancelling that term's bits
        and leaving its order atom behind."""
        steps = [f"@lin{self.index}"]
        for i, value in enumerate(bounds):
            if i != ignoring and value is not None:
                steps += [self.channelling(i, value), "+"]
        return steps

    def propagate(self, state) -> Inference:
        # Read once, before anything is narrowed, so that every bound below is
        # worked out from the same starting point -- and so that what the proof
        # adds up is what the arithmetic was actually done with.
        smallest = [self.smallest(state, i) for i in range(len(self.scope))]
        bounds = self.bound_values(state)
        total = sum(smallest)

        if total > self.rhs:
            # Even at their smallest these terms overshoot.  Adding every bound
            # to @lin leaves something that cannot be satisfied.
            return state.fail(Pol(tuple(self.steps(bounds) + ["s"])))

        result = Inference.NO_CHANGE
        for i, x in enumerate(self.scope):
            # Everything else is at least this much, so this term has at most
            # the rest of the budget to play with.
            budget = self.rhs - (total - smallest[i])
            # The same sum again, but leaving this term's own bound out and
            # putting in the bound we are about to claim instead.
            claimed = budget + 1 if self.coefficients[i] > 0 else -budget
            because = Pol(
                tuple(
                    self.steps(bounds, ignoring=i)
                    + [self.channelling(i, claimed), "+", "s"]
                )
            )
            if self.coefficients[i] > 0:
                result = max(result, state.set_upper_bound(x, budget, because))
            else:
                result = max(result, state.set_lower_bound(x, -budget, because))
            if result is Inference.CONTRADICTION:
                return result
        return result
