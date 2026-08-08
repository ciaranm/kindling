"""The .pbp file: everything the solver did, and why it was allowed to.

The proof has two kinds of line in it and they have very different characters.

Propagators contribute *implications*: "if these atoms held then this one
holds".  Those are true at the root of the search, not just at the node that
noticed them, which is what makes them safe to leave lying around -- nothing
ever has to be retracted, so there is no deletion anywhere in kindling.

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

from ..justify import Assert
from ..model import Model
from .names import neg


def clause(literals) -> str:
    """A disjunction, as a pseudo-Boolean constraint.  An empty one is a
    contradiction, and comes out as ">= 1" with nothing on the left."""
    terms = " ".join(f"1 {lit}" for lit in literals)
    return f"{terms} >= 1".lstrip()


def inference_clause(atom: str, because) -> list[str]:
    """"if the reason held then this atom holds", as a disjunction."""
    return [neg(r) for r in because.reason] + [atom]


def failure_clause(because) -> list[str]:
    """"the reason cannot all hold at once", as a disjunction.  A failure has
    no inferred atom, so this is the same thing with nothing on the end."""
    return [neg(r) for r in because.reason]


class NoProof:
    """What the solver logs to when nobody asked for a proof.  Being an object
    with the same methods rather than a None to check means the solver has no
    idea whether proof logging is on, and cannot get it wrong."""

    def comment(self, text: str = "") -> None:
        pass

    def preamble(self, model: Model) -> None:
        pass

    def infer(self, atom: str, because) -> None:
        pass

    def failed(self, because) -> None:
        pass

    def node_failed(self, decisions) -> None:
        pass

    def finish(self, proved_unsatisfiable: bool) -> None:
        pass


class ProofLog(NoProof):
    def __init__(self, out: TextIO) -> None:
        self.out = out
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

    def infer(self, atom: str, because) -> None:
        """One propagation: the reason held, so this atom holds too."""
        self.emit(inference_clause(atom, because), because)

    def failed(self, because) -> None:
        """A propagator says this node is hopeless."""
        self.emit(failure_clause(because), because)

    def emit(self, literals, because) -> None:
        if isinstance(because, Assert):
            self.assertions.append(because.name)
            self.write(f"a {clause(literals)} : : {because.name} ;")
        else:
            raise AssertionError(f"no way to write {type(because).__name__} yet")

    def node_failed(self, decisions) -> None:
        self.write(f"rup {clause([neg(d) for d in decisions])} ;")

    def finish(self, proved_unsatisfiable: bool) -> None:
        self.write("output NONE;")
        self.write(f"conclusion {'UNSAT' if proved_unsatisfiable else 'NONE'};")
        self.write("end pseudo-Boolean proof;")
