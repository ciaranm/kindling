"""Everything that changes during search, and the only place it can change.

A variable is a lightweight handle -- an index, an upper bound and a name, all
fixed when the model is built.  The part that moves is here, keyed by that
index.  So there is exactly one mutable object in the solver, and exactly one
set of methods that can mutate it, and every one of them demands a
justification.  That is the whole reason for splitting it this way: if you want
to know everything that can happen to a domain, you read this file and you are
done.

Decisions are the one exception, and deliberately so.  An assumption is not an
inference -- nothing is being claimed to follow from anything -- so assume()
takes no justification.  What makes the assumption sound is that the search
tries the other branch too, and the proof says so.
"""

from __future__ import annotations

from enum import IntEnum

from .domain import Domain
from .justify import Justification
from .model import Model, Variable
from .proof.log import NoProof
from .proof.names import eq, ge, neg


class Inference(IntEnum):
    """What an attempt to narrow a domain achieved.  Ordered, so that a
    propagator can combine several with max() and keep the worst news."""

    NO_CHANGE = 0
    CHANGED = 1
    CONTRADICTION = 2


class State:
    def __init__(self, model: Model, log=None) -> None:
        self.model = model
        self.log = log if log is not None else NoProof()
        self.domains = [Domain(x.ub) for x in model.variables]
        self.decisions: list[str] = []  # the atoms we assumed to get here
        self.changed: set[int] = set()  # variable indices, for the queue

    def clone(self) -> State:
        """A child node's state.  Nothing is shared except the model, which
        never changes, so a child can never disturb its parent."""
        child = State.__new__(State)
        child.model = self.model
        child.log = self.log
        child.domains = [d.copy() for d in self.domains]
        child.decisions = list(self.decisions)
        child.changed = set()
        return child

    # --- looking at domains -------------------------------------------------

    def domain(self, x: Variable) -> Domain:
        return self.domains[x.index - 1]

    def lower_bound(self, x: Variable) -> int:
        return self.domain(x).lower_bound()

    def upper_bound(self, x: Variable) -> int:
        return self.domain(x).upper_bound()

    def is_assigned(self, x: Variable) -> bool:
        return self.domain(x).is_assigned()

    def value(self, x: Variable) -> int:
        return self.domain(x).value()

    # --- changing domains ---------------------------------------------------

    def remove(self, x: Variable, value: int, because: Justification) -> Inference:
        """x is not value."""
        return self._narrowed(
            x, self.domain(x).remove(value), neg(eq(x.index, value)), because
        )

    def set_lower_bound(
        self, x: Variable, bound: int, because: Justification
    ) -> Inference:
        """x is at least bound."""
        if bound > x.ub:
            # There is no atom for "x >= something above its declared range",
            # so this is not a narrowing at all -- it is a failure.
            return self.fail(because)
        return self._narrowed(
            x, self.domain(x).remove_below(bound), ge(x.index, bound), because
        )

    def set_upper_bound(
        self, x: Variable, bound: int, because: Justification
    ) -> Inference:
        """x is at most bound."""
        if bound < 0:
            return self.fail(because)
        return self._narrowed(
            x, self.domain(x).remove_above(bound), neg(ge(x.index, bound + 1)), because
        )

    def fail(self, because: Justification) -> Inference:
        """This node cannot lead to a solution."""
        # The line that closes the node is written by the search, not here;
        # what a propagator owes is whatever makes that line checkable.
        self.log.failed(because)
        return Inference.CONTRADICTION

    def _narrowed(
        self, x: Variable, changed: bool, atom: str, because: Justification
    ) -> Inference:
        """The chokepoint.  Every domain change in the solver arrives here,
        which is why the proof only has to be written in one place."""
        if not changed:
            # Saying CHANGED when nothing changed would let propagation loop
            # forever, so this has to be honest.
            return Inference.NO_CHANGE
        self.log.infer(atom, because)
        self.changed.add(x.index)
        if self.domain(x).is_empty():
            return Inference.CONTRADICTION
        return Inference.CHANGED

    # --- decisions ----------------------------------------------------------

    def assume_equal(self, x: Variable, value: int) -> None:
        self.decisions.append(eq(x.index, value))
        self.domain(x).remove_below(value)
        self.domain(x).remove_above(value)
        self.changed.add(x.index)

    def assume_not_equal(self, x: Variable, value: int) -> None:
        self.decisions.append(neg(eq(x.index, value)))
        self.domain(x).remove(value)
        self.changed.add(x.index)
