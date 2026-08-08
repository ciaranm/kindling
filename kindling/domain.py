"""The values a variable can still take.

A set, so that values can go from the middle and not just the ends -- table
propagation and all_different both need that.  In C++ this would be a
std::set<int> and you would get the ordering for free; Python's sets have no
order at all, so anything that leaves this class in a way that could reach the
proof file goes through sorted().  Proof output that changes between runs is
proof output nobody can diff, and diffing is how you debug a proof.
"""

from __future__ import annotations


class Domain:
    def __init__(self, ub: int) -> None:
        self._values = set(range(ub + 1))

    def copy(self) -> Domain:
        clone = Domain.__new__(Domain)
        clone._values = set(self._values)
        return clone

    def __contains__(self, value: int) -> bool:
        return value in self._values

    def __len__(self) -> int:
        return len(self._values)

    def __iter__(self):
        return iter(sorted(self._values))

    def __repr__(self) -> str:
        return "{" + ", ".join(str(v) for v in self) + "}"

    def lower_bound(self) -> int:
        return min(self._values)

    def upper_bound(self) -> int:
        return max(self._values)

    def is_empty(self) -> bool:
        return not self._values

    def is_assigned(self) -> bool:
        return len(self._values) == 1

    def value(self) -> int:
        """The one remaining value.  Only ask when is_assigned()."""
        (value,) = self._values
        return value

    def remove(self, value: int) -> bool:
        """Returns whether this actually changed anything."""
        if value not in self._values:
            return False
        self._values.discard(value)
        return True

    def remove_below(self, bound: int) -> bool:
        """Drop everything less than bound."""
        gone = {v for v in self._values if v < bound}
        self._values -= gone
        return bool(gone)

    def remove_above(self, bound: int) -> bool:
        """Drop everything greater than bound."""
        gone = {v for v in self._values if v > bound}
        self._values -= gone
        return bool(gone)
