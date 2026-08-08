"""Why an inference is allowed.

Every narrowing of a domain has to say why, because every narrowing turns into
a line of the proof and a line of the proof has to be checkable.  The argument
is passed in rather than worked out afterwards: by the time the domain has
changed, the reason it changed is gone.

Right now there is exactly one kind, and it is the dishonest one.  Assert says
"take my word for it", and comes out as veripb's `a` rule -- the proof is then
structurally complete and the checker will confirm everything except the thing
you asserted, reporting UNDER ASSERTIONS instead of VERIFIED.  Turning these
into real derivations, one at a time, is what the exercises are.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Justification:
    """Base class: how a checker should be persuaded of one inference."""


@dataclass(frozen=True)
class Assert(Justification):
    """Not checked.  The name is carried into the proof as an annotation so
    that the burn-down tool can say what is left to do."""

    name: str
