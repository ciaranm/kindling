"""Depth-first search, by cloning.

Each node gets its own state, copied from its parent, so nothing a child does
can be seen by anything else and there is no undoing to get wrong.  A real
solver would trail the changes and roll them back, which is far faster and far
harder to follow; here the copy is the point.

Branching is binary: pick a variable, try it equal to a value, then try it not
equal to that value.  Two branches rather than one per value keeps the proof's
shape simple.

Everything this file contributes to the proof is the one line at the bottom of
each dead end, saying that the decisions leading there cannot all hold.  A node
whose children have both failed is a dead end too, and the root is a dead end
with no decisions in it, so the line that finishes the proof is the same line as
all the others.
"""

from __future__ import annotations

from .model import Model, Variable
from .propagate import propagate
from .proof.log import NoProof
from .state import Inference, State


def smallest_domain(state: State) -> Variable | None:
    """The unassigned variable with the fewest values left, ties going to the
    lowest index so that runs are repeatable."""
    candidates = [x for x in state.model.variables if not state.is_assigned(x)]
    if not candidates:
        return None
    return min(candidates, key=lambda x: (len(state.domain(x)), x.index))


def search(model: Model, state: State) -> dict[Variable, int] | None:
    if propagate(model, state) is Inference.CONTRADICTION:
        state.log.node_failed(state.decisions)
        return None

    x = smallest_domain(state)
    if x is None:
        return {v: state.value(v) for v in model.variables}

    value = state.lower_bound(x)

    left = state.clone()
    left.assume_equal(x, value)
    state.log.comment(f"decide {x} = {value}")
    if (solution := search(model, left)) is not None:
        return solution

    right = state.clone()
    right.assume_not_equal(x, value)
    state.log.comment(f"decide {x} != {value}")
    if (solution := search(model, right)) is not None:
        return solution

    # Both ways out of here are dead, so this node is dead as well.
    state.log.node_failed(state.decisions)
    return None


def solve(model: Model, log=None) -> dict[Variable, int] | None:
    """A solution, or None if there is not one.  Pass a ProofLog to get a
    proof; without one the solver does not know it is being watched."""
    log = log if log is not None else NoProof()
    log.preamble(model)
    solution = search(model, State(model, log))
    log.finish(proved_unsatisfiable=solution is None)
    return solution
