"""The .pbp file: everything the solver did, and why it was allowed to.

The proof has two kinds of line in it and they have very different characters.

Propagators contribute *implications*: "if the guesses that got us here all
held, then this atom holds".  Those are true at the root of the search, not
just at the node that noticed them, which is what makes them safe to leave
lying around -- nothing ever has to be retracted, so there is no deletion
anywhere in kindling.  See justify.py for why the guesses, and what a real
solver would say instead.

The search contributes one line per failed node, saying that the decisions
that led there cannot all hold.  That line is reverse unit propagation every
time and needs no help from anyone: replaying the implications above under
those decisions reaches the same contradiction the solver reached.  So the
entire proof of the search is one line per node, and all the difficulty lives
in the propagators, which is where we want the students looking.

Both kinds are written with veripb's arrow, so a line of the proof says the
implication it means rather than the row it becomes.  The last failed node is
the root, whose decision list is empty, so nothing is conditional on anything,
and the line that closes the proof is the same line as all the others with
everything left out of it.
"""

from __future__ import annotations

from typing import TextIO

from ..justify import Assert, Pol
from ..model import Model

CONTRADICTION = ">= 1"
"""A sum of nothing, which cannot reach one.  On its own it is the line that
closes the proof; on the right of an arrow it says the guesses on the left
cannot all hold."""


def holds(atom: str) -> str:
    """The constraint saying this atom is true."""
    return f"1 {atom} >= 1"


def given(guesses, consequent: str) -> str:
    """"if all of these hold, then that", in veripb's notation.

    `g1 g2 ==> 1 xx >= 1` is one pseudo-Boolean constraint and not two: the
    checker reads the arrow and carries each guess's negation into the row at
    the degree, so what it ends up with here is "~g1 or ~g2 or xx".  We could
    write that row out ourselves and not a thing about the checking would
    change.  The arrow is here because a proof is for reading, and this way a
    line of it says what the propagator meant rather than what it normalises
    to.

    With nothing to be conditional on there is no arrow, and the consequent
    stands by itself.
    """
    return f"{' '.join(guesses)} ==> {consequent}" if guesses else consequent


class NoProof:
    """What the solver logs to when nobody asked for a proof.  Being an object
    with the same methods rather than a None to check means the solver has no
    idea whether proof logging is on, and cannot get it wrong."""

    def comment(self, text: str = "") -> None:
        pass

    def preamble(self, model: Model) -> None:
        pass

    def infer(self, atom: str, because, guesses) -> None:
        pass

    def failed(self, because, guesses) -> None:
        pass

    def node_failed(self, decisions) -> None:
        pass

    def finish(self, proved_unsatisfiable: bool) -> None:
        pass


class ProofLog(NoProof):
    """With justifications turned off, this writes the search and nothing else.

    Every propagation still happens; not a word of it reaches the file.  That
    is not a way to ship a solver, and it is not an exercise either.  It is
    here so you can watch what a proof looks like with the propagators left out
    of it, and find out that the answer is sometimes "still fine" and sometimes
    "rejected".  Which of those you get is the whole subject.
    """

    def __init__(self, out: TextIO, justifications: bool = True) -> None:
        self.out = out
        self.justifications = justifications
        self.assertions: list[str] = []
        self.out.write("pseudo-Boolean proof version 3.0\n")

    def write(self, line: str) -> None:
        self.out.write(line + "\n")

    def comment(self, text: str = "") -> None:
        self.write(f"% {text}".rstrip())

    def preamble(self, model: Model) -> None:
        """Every variable takes at least one of its values.

        That is a consequence of what the direct atoms mean rather than
        something the model says, so the .opb does not assert it and we derive
        it here.  Adding up the rows that define x = v for each v in turn makes
        every order atom cancel against its own negation, and the telescope
        collapses to exactly this.  all_different needs it; nothing else does.
        """
        self.comment("every variable takes at least one value, by telescoping")
        self.comment("the rows that define its direct atoms")
        for x in model.variables:
            steps = [f"@x{x.index}eq0_dn"]
            for v in range(1, x.ub + 1):
                steps += [f"@x{x.index}eq{v}_dn", "+"]
            self.write(f"@atleast{x.index} pol {' '.join(steps)} ;")
        self.comment()

    def infer(self, atom: str, because, guesses) -> None:
        """One propagation: the guesses hold, so this atom holds too."""
        if not self.justifications:
            return
        if isinstance(because, Pol):
            self.steps(because)
        self.claim(given(guesses, holds(atom)), because)

    def failed(self, because, guesses) -> None:
        """A propagator says this node is hopeless.

        Nothing needs claiming here.  The line the search writes at the bottom
        of a dead node says exactly this and says it as a rup, so a propagator
        that could have made the claim by rup need not say anything at all, and
        one that needs cutting planes only has to leave the right row behind.
        """
        if not self.justifications:
            return
        if isinstance(because, Pol):
            self.steps(because)
        elif isinstance(because, Assert):
            self.claim(given(guesses, CONTRADICTION), because)

    def steps(self, because: Pol) -> None:
        self.write(f"pol {' '.join(because.steps)} ;")

    def claim(self, constraint: str, because) -> None:
        if isinstance(because, Assert):
            self.assertions.append(because.name)
            self.write(f"a {constraint} : : {because.name} ;")
        else:
            self.write(f"rup {constraint} ;")

    def node_failed(self, decisions) -> None:
        self.write(f"rup {given(decisions, CONTRADICTION)} ;")

    def finish(self, proved_unsatisfiable: bool) -> None:
        self.write("output NONE;")
        self.write(f"conclusion {'UNSAT' if proved_unsatisfiable else 'NONE'};")
        self.write("end pseudo-Boolean proof;")
