"""Why an inference is allowed.

Every narrowing of a domain has to say why, because every narrowing turns into
a line of the proof and a line of the proof has to be checkable.  The argument
is passed in rather than worked out afterwards: by the time the domain has
changed, the reason it changed is gone.

A justification has two halves.  The *reason* is the list of atoms that were
already true and that forced the inference; together with the inferred atom it
makes a clause, "if all of these held then that one holds", and that clause is
true at the root of the search and not just at the node that noticed it.  The
rest of the justification says how a checker should be persuaded of the clause.

Right now there is one way, and it is the dishonest one.  Assert says "take my
word for it" and comes out as veripb's `a` rule, so the proof is structurally
complete and the checker confirms everything except the assertions themselves,
reporting UNDER ASSERTIONS rather than VERIFIED.  Note that the constraint an
Assert claims is exactly the constraint a real derivation would have to
produce, so turning one into the other changes a single word and nothing else.
That is what the exercises are.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Assert:
    """Not checked.  The name is carried into the proof as an annotation so
    that the burn-down tool can say what is left to do."""

    name: str
    reason: tuple[str, ...] = field(default=())


Justification = Assert  # stage 4 widens this to Assert | Rup | Pol
