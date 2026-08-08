"""Depth-first search, by cloning.

Each node gets its own state, copied from its parent, so nothing a child does
can be seen by anything else and there is no undoing to get wrong.  A real
solver would trail the changes and roll them back, which is far faster and far
harder to follow; here the copy is the point.

Branching is binary: pick a variable, try it equal to a value, then try it not
equal to that value.  Two branches rather than one per value keeps the proof's
shape simple -- each failed node contributes exactly one line, negating the
decisions that led to it.
"""

from __future__ import annotations

from .model import Model, Variable
from .propagate import propagate
from .state import Inference, State


def smallest_domain(state: State) -> Variable | None:
    """The unassigned variable with the fewest values left, ties going to the
    lowest index so that runs are repeatable."""
    candidates = [x for x in state.model.variables if not state.is_assigned(x)]
    if not candidates:
        return None
    return min(candidates, key=lambda x: (len(state.domain(x)), x.index))


def solve(model: Model, state: State | None = None) -> dict[Variable, int] | None:
    """A solution, or None if there is not one."""
    state = State(model) if state is None else state

    if propagate(model, state) is Inference.CONTRADICTION:
        return None

    x = smallest_domain(state)
    if x is None:
        return {v: state.value(v) for v in model.variables}

    value = state.lower_bound(x)

    left = state.clone()
    left.assume_equal(x, value)
    if (solution := solve(model, left)) is not None:
        return solution

    right = state.clone()
    right.assume_not_equal(x, value)
    return solve(model, right)
