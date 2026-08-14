"""The .pbp file: everything the solver did, and why it was allowed to.

The proof has two kinds of line in it and they have very different characters.

Propagators contribute *implications*: "if the guesses that got us here all
held, then this atom holds".  Those are true at the root of the search, not
just at the node that noticed them, which is what makes them safe to leave
lying around -- nothing ever has to be retracted, so there is no deletion
anywhere in kindling.  See justify.py for why the guesses, and what a real
solver would say instead.

The search contributes one line per failed node, negating the decisions that
led to it.  That line is reverse unit propagation every time and needs no help
from anyone: replaying the implications above under those decisions reaches
the same contradiction the solver reached.  So the entire proof of the search
is one line per node, and all the difficulty lives in the propagators, which
is where we want the students looking.

The last failed node is the root, whose decision list is empty, so the line
that closes the proof is the same line as all the others with nothing in it.
"""

from __future__ import annotations

from typing import TextIO

from ..justify import Assert, Pol
from ..model import Model
from .names import neg


def clause(literals) -> str:
    """A disjunction, as a pseudo-Boolean constraint.  An empty one is a
    contradiction, and comes out as ">= 1" with nothing on the left."""
    terms = " ".join(f"1 {lit}" for lit in literals)
    return f"{terms} >= 1".lstrip()


def inference_clause(atom: str, guesses) -> list[str]:
    """"if the guesses all held then this atom holds", as a disjunction."""
    return [neg(g) for g in guesses] + [atom]


def failure_clause(guesses) -> list[str]:
    """"the guesses cannot all hold at once", as a disjunction.  A failure has
    no inferred atom, so this is the same thing with nothing on the end."""
    return [neg(g) for g in guesses]


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
        literals = inference_clause(atom, guesses)
        if isinstance(because, Pol):
            self.steps(because)
        self.claim(literals, because)

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
            self.claim(failure_clause(guesses), because)

    def steps(self, because: Pol) -> None:
        self.write(f"pol {' '.join(because.steps)} ;")

    def claim(self, literals, because) -> None:
        if isinstance(because, Assert):
            self.assertions.append(because.name)
            self.write(f"a {clause(literals)} : : {because.name} ;")
        else:
            self.write(f"rup {clause(literals)} ;")

    def node_failed(self, decisions) -> None:
        self.write(f"rup {clause([neg(d) for d in decisions])} ;")

    def finish(self, proved_unsatisfiable: bool) -> None:
        self.write("output NONE;")
        self.write(f"conclusion {'UNSAT' if proved_unsatisfiable else 'NONE'};")
        self.write("end pseudo-Boolean proof;")
