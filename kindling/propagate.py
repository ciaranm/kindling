"""Run the propagators until nothing more happens.

The queue holds constraints that might still have something to say.  A
constraint goes back on it when a variable it watches has changed, including
when it was the constraint itself that changed it -- a propagator is allowed
not to reach its own fixpoint in one call, and re-running it until it says
NO_CHANGE is cheaper to understand than proving it never needs to be.

That does mean NO_CHANGE has to mean no change.  A propagator that reports
having done something when it has not will spin here forever.
"""

from __future__ import annotations

from collections import deque

from .model import Model
from .state import Inference, State


def watchers(model: Model) -> dict[int, list[int]]:
    """Which constraints care about each variable.  Rebuilt per call, which is
    wasteful and not worth fixing at this size."""
    result: dict[int, list[int]] = {}
    for position, constraint in enumerate(model.constraints):
        for x in constraint.variables():
            result.setdefault(x.index, []).append(position)
    return result


def propagate(model: Model, state: State) -> Inference:
    interested = watchers(model)
    queued = set(range(len(model.constraints)))
    queue = deque(sorted(queued))

    while queue:
        position = queue.popleft()
        queued.discard(position)

        state.changed.clear()
        result = model.constraints[position].propagate(state)
        if result is Inference.CONTRADICTION:
            return result

        for index in sorted(state.changed):
            for other in interested.get(index, []):
                if other not in queued:
                    queued.add(other)
                    queue.append(other)

    return Inference.NO_CHANGE
