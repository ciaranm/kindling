"""Why an inference is allowed.

Every narrowing of a domain has to say why, because every narrowing becomes a
line of the proof and a line of the proof has to be checkable.

What gets logged is an implication: "if all the guesses that got us to this
node hold, then this literal holds too", and it goes into the proof with an
arrow in it so that it reads the way it was meant.  That is true at the root
and not only at the node that noticed it, which is what makes it safe to leave
lying around -- nothing is ever retracted, so kindling has no deletion in it
anywhere.

Using the guesses is the crude option, and it is always available.  A real
solver states a *reason* instead: the handful of literals the propagator
actually looked at, which is usually far fewer than every guess made on the
way here.  Both are valid.  What makes the line legal is that reverse unit
propagation can get from the left-hand side to the right-hand side, and the
guesses always suffice for that, because between them they determine the whole
node.

The reason version is worth knowing about even though kindling does not do it,
because it is the same clause a lazy clause generation solver has to produce to
explain a propagation, and it is better for the same reasons: the proof is
smaller, the checker's replay is shorter, and in an LCG solver it is what makes
the learnt clause worth learning.  On the too-small instance, the same
refutation logged with guesses spends 4558 literals across its 422 clause
bodies, and with real reasons it spends 2895.  Working the reason out is real
work though, and it is work about propagators rather than about proofs, so
kindling spends the space and keeps the attention on the derivations.

There is a second thing the crude option buys.  A reason can be *wrong* -- cite
too little and the clause is not implied by anything, and since an asserted
line is checked by nobody the mistake surfaces much later, as a derivation that
cannot be made to produce it.  Guesses are read off the state rather than
worked out, so that whole class of mistake does not exist, and the only way a
logged line can fail is if its derivation is wrong.  Which is exactly the thing
the exercises are about.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Assert:
    """Not checked.  Comes out as veripb's `a` rule, so the proof is
    structurally complete and the checker confirms everything except the
    assertions themselves, reporting UNDER ASSERTIONS rather than VERIFIED.

    The name is carried into the proof as an annotation, so that the burn-down
    can say what is left to do.  The hint is carried beside it and says what
    this particular assertion was about.  An assertion is a claim with its
    working thrown away, and the working is exactly what you want back when the
    job in front of you is to replace it with a derivation: the propagator knew
    which variables and which values it was talking about, and nobody reading
    the line afterwards can recover them.

    Free text as far as veripb is concerned -- any character but "%" and ";" --
    so it is for a person, or for somebody else's justifier, and never for the
    checker.  Nothing about the proof changes if it is wrong, which is the same
    warning that applies to the assertion above it."""

    name: str
    hint: str = ""




@dataclass(frozen=True)
class Rup:
    """Checked, by reverse unit propagation: the checker assumes the clause is
    false and propagates everything it knows, and the claim stands if that
    reaches a contradiction.  Costs nothing to write and does a surprising
    amount, but it cannot combine two constraints -- for that, see Pol."""


@dataclass(frozen=True)
class Pol:
    """Checked, by cutting planes: a recipe for building a new PB constraint out
    of ones the checker already has, in reverse Polish.  "@a @b + s" means add
    @b to @a and saturate the result.

    The steps do not have to land exactly on the clause being claimed.  For an
    inference, kindling writes the steps and then a rup of the clause, so the
    steps only have to get the checker close enough to finish on its own.  For
    a failure it writes the steps alone, because the line the search puts at
    the bottom of a dead node is already the claim, and it is a rup too.
    """

    steps: tuple[str, ...]


Justification = Assert | Rup | Pol
