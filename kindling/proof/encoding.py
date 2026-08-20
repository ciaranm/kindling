"""How an integer variable becomes pseudo-Boolean.

Every variable gets all three layers, written out in full the moment it is
defined.  Nothing is created lazily, which costs a lot of constraints and buys
the thing that matters here: at no point does anyone have to think about
whether a literal exists yet.

    bits    x{i}b{k}     x{i} = sum of 2^k * x{i}b{k}
    order   x{i}ge{v}    x{i} >= v
    direct  x{i}eq{v}    x{i} = v

The layers are not interchangeable.  Linear constraints are written over the
bits, because that is the only layer where arithmetic is cheap.  Propagators
reason in order and direct literals, because that is what a domain is made
of.
Moving between the two is what most of a kindling proof is doing, and the
channelling constraints below are what makes it possible.

An order encoding usually also carries chain constraints saying x >= v implies
x >= v-1.  There are none here, and they are not an oversight: with the bits
underneath, every order and direct literal of a variable is already connected
to
every other one through them, so the chain is not merely implied but implied
*by unit propagation*, which is the part that actually matters.  Checking an
implication means assuming both the premise and the negated conclusion, and
whichever of those pins some bits does the work -- asserting an order literal
bounds the bits from below, negating one bounds them from above, and between
them nothing is left.  tests/test_proof_model.py checks that every
literal-to-literal implication really is reverse unit propagation, over
several domain sizes,
because this is the sort of claim that is easy to believe and wrong.
"""

from __future__ import annotations

from .names import bits, eq, ge, nbits, neg, top
from .opb import OpbFile


def define_variable(opb: OpbFile, index: int, ub: int, name: str = "") -> None:
    """Write every constraint that says what one variable's literals mean."""
    n, ceiling = nbits(ub), top(ub)
    value = " + ".join(f"{2**k}*x{index}b{k}" for k in reversed(range(n)))

    opb.comment()
    opb.comment(f"--- x{index} in [0, {ub}]" + (f", the model's {name}" if name else "") + " ---")
    opb.comment(f"x{index} = {value}")

    # The bits can represent more than the domain allows whenever ub is not one
    # less than a power of two, so say so.
    if ceiling > ub:
        opb.constraint(f"x{index}_ub", bits(index, ub), "<=", ub)

    opb.comment()
    opb.comment(f"x{index}ge{{v}} means x{index} >= v, in both directions at once.")
    opb.comment(f"Each line is two constraints: _up is x{index}ge{{v}} ==> {value} >= v,")
    opb.comment(f"and _dn is x{index}ge{{v}} <== {value} >= v.")
    for v in range(1, ub + 1):
        opb.reified(
            [f"x{index}ge{v}_up", f"x{index}ge{v}_dn"],
            ge(index, v),
            "<==>",
            bits(index, ub),
            v,
        )

    opb.comment(f"x{index}eq{{v}} means x{index} = v, which is x{index}ge{{v}} and not x{index}ge{{v+1}}")
    opb.comment("A conjunction is a pseudo-Boolean constraint too: asking for all")
    opb.comment("of n literals is asking for their sum to be at least n.")
    for v in range(0, ub + 1):
        conjuncts = []
        if v > 0:
            conjuncts.append(ge(index, v))
        if v < ub:
            conjuncts.append(neg(ge(index, v + 1)))
        opb.reified(
            [f"x{index}eq{v}_up", f"x{index}eq{v}_dn"],
            eq(index, v),
            "<==>",
            [(1, literal) for literal in conjuncts],
            len(conjuncts),
        )


def define_proof_model(model) -> OpbFile:
    """The whole .opb: every variable, then every constraint."""
    opb = OpbFile()
    opb.comment("kindling proof model")
    opb.comment()
    opb.comment(f"{len(model.variables)} variables, {len(model.constraints)} constraints")
    for var in model.variables:
        define_variable(opb, var.index, var.ub, var.name)
    for constraint in model.constraints:
        opb.comment()
        constraint.define_proof_model(opb)
    return opb
