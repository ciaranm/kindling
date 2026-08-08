"""What everything is called in the proof.

Atom names are meant to be read.  Variable x3 having the value 2 is "x3eq2",
and being at least 2 is "x3ge2", so a line of a proof can usually be read out
loud without consulting anything.

Two rules from veripb constrain us: an atom name must be at least two
characters and must start with a letter or an underscore, and although "-" is
a legal character it reads like subtraction.  Non-negative domains mean no
name ever contains one.
"""

from __future__ import annotations


def bit(var: int, k: int) -> str:
    """The 2^k bit of x{var}."""
    return f"x{var}b{k}"


def ge(var: int, value: int) -> str:
    """x{var} >= value."""
    return f"x{var}ge{value}"


def eq(var: int, value: int) -> str:
    """x{var} = value."""
    return f"x{var}eq{value}"


def selector(constraint: int, tuple_index: int) -> str:
    """"the table in constraint {constraint} is using tuple {tuple_index}"."""
    return f"c{constraint}t{tuple_index}"


def neg(literal: str) -> str:
    """The negation of a literal, which is a "~" on the front, or the removal
    of the one that is already there."""
    return literal[1:] if literal.startswith("~") else "~" + literal


def nbits(ub: int) -> int:
    """How many bits it takes to represent every value in [0, ub]."""
    return max(1, ub.bit_length())


def bits(var: int, ub: int, negated: bool = False) -> list[tuple[int, str]]:
    """x{var} as weighted bit literals, most significant first.

    With negated=True this is (top - x{var}) instead, where top is the largest
    value the bits can represent -- which is how you say "x is small" in a
    format that only has >= constraints.
    """
    return [
        (2**k, neg(bit(var, k)) if negated else bit(var, k))
        for k in reversed(range(nbits(ub)))
    ]


def top(ub: int) -> int:
    """The largest value the bits of a variable with this bound can hold.  Not
    the same as ub unless ub is one less than a power of two."""
    return 2 ** nbits(ub) - 1
