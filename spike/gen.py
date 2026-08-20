#!/usr/bin/env python3
"""Throwaway OPB generator for the kindling stage-0 spike.

Not the real thing -- this exists so the hand-written .pbp files in this
directory have something to be checked against, and so that stage 1 has a
worked reference for what the encoding actually has to look like.

Variables are x1..xn, each with domain [0, ub].  Every variable gets all three
layers of the encoding, eagerly:

  bits   x{i}b{k}     x{i} = sum of 2^k * x{i}b{k}
  order  x{i}ge{v}    "x{i} >= v", channelled to the bits both ways
  direct x{i}eq{v}    "x{i} = v", defined from the order literals

Linear constraints are written over the bits; all_different and table are
written over the direct literals.
"""

import sys


def nbits(ub):
    return max(1, ub.bit_length())


def bit_sum(i, ub, negated=False):
    tilde = "~" if negated else ""
    return " ".join(
        f"{2 ** k} {tilde}x{i}b{k}" for k in reversed(range(nbits(ub)))
    )


def variable_constraints(i, ub):
    """The whole encoding of one variable."""
    top = 2 ** nbits(ub) - 1  # largest value the bits can represent
    out = [
        f"* --- x{i} in [0, {ub}] ---",
        f"* x{i} = {' + '.join(f'{2 ** k}*x{i}b{k}' for k in reversed(range(nbits(ub))))}",
    ]
    if top > ub:
        out.append(f"@x{i}_ub {bit_sum(i, ub)} <= {ub} ;")

    out += [
        f"* order literals: x{i}ge{{v}} means x{i} >= v, channelled to the"
        " bits both ways.",
        "* these are the big-M forms of what the solver, which came later,",
        "* writes with veripb's arrow syntax as",
        f"*     x{i}ge{{v}} ==> {bit_sum(i, ub)} >= v      (_up)",
        f"*     x{i}ge{{v}} <== {bit_sum(i, ub)} >= v      (_dn)",
    ]
    for v in range(1, ub + 1):
        # x{i}ge{v} -> x{i} >= v
        out.append(f"@x{i}ge{v}_up {bit_sum(i, ub)} {v} ~x{i}ge{v} >= {v} ;")
        # x{i} >= v -> x{i}ge{v}, written on the "top - x" side
        out.append(
            f"@x{i}ge{v}_dn {bit_sum(i, ub, negated=True)} "
            f"{top - v + 1} x{i}ge{v} >= {top - v + 1} ;"
        )
    for v in range(2, ub + 1):
        out.append(f"@x{i}ge{v}_chain 1 ~x{i}ge{v} 1 x{i}ge{v - 1} >= 1 ;")

    out.append(
        f"* direct literals: x{i}eq{{v}} <-> x{i}ge{{v}} and not x{i}ge{{v+1}}"
    )
    for v in range(0, ub + 1):
        # the conjunction that defines x{i}eq{v}, as (name, negated) pairs
        conj = []
        if v > 0:
            conj.append((f"x{i}ge{v}", False))
        if v < ub:
            conj.append((f"x{i}ge{v + 1}", True))
        # x{i}eq{v} -> each conjunct
        for j, (name, neg) in enumerate(conj):
            lit = f"{'~' if neg else ''}{name}"
            out.append(f"@x{i}eq{v}_up{j} 1 ~x{i}eq{v} 1 {lit} >= 1 ;")
        # all the conjuncts -> x{i}eq{v}, ie the clause with each one negated
        rest = " ".join(f"1 {'' if neg else '~'}{name}" for name, neg in conj)
        out.append(f"@x{i}eq{v}_dn 1 x{i}eq{v} {rest} >= 1 ;")
    return out


def linear_le(c, coeffs, ubs, rhs):
    """sum of +/-1 * x{i} <= rhs, written over the bits."""
    terms = []
    for (sign, i), ub in zip(coeffs, ubs):
        for k in reversed(range(nbits(ub))):
            terms.append(f"{sign * 2 ** k} x{i}b{k}")
    return [
        "* " + " + ".join(f"{'-' if s < 0 else ''}x{i}" for s, i in coeffs)
        + f" <= {rhs}",
        f"@lin{c} {' '.join(terms)} <= {rhs} ;",
    ]


def all_different(c, ids, values):
    out = [f"* all_different({', '.join(f'x{i}' for i in ids)})"]
    for v in values:
        terms = " ".join(f"1 x{i}eq{v}" for i in ids)
        out.append(f"@amo{c}_{v} {terms} <= 1 ;")
    return out


def table(c, ids, tuples):
    out = [f"* table({', '.join(f'x{i}' for i in ids)}) with {len(tuples)} tuples"]
    sel = " ".join(f"1 c{c}t{j}" for j in range(len(tuples)))
    out.append(f"@tbl{c}_sel {sel} >= 1 ;")
    for j, tup in enumerate(tuples):
        for i, v in zip(ids, tup):
            out.append(f"@tbl{c}t{j}_{i} 1 ~c{c}t{j} 1 x{i}eq{v} >= 1 ;")
    return out


def render(title, ubs, constraints):
    """ubs is a dict {var index: upper bound}; constraints a list of lists of
    rendered PB constraints."""
    out = [f"* {title}"]
    for i in sorted(ubs):
        out += variable_constraints(i, ubs[i])
    for constraint in constraints:
        out += constraint
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    sys.stderr.write("gen.py is imported by the per-example build scripts\n")
