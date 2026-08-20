"""The .opb file: what the problem means, in pseudo-Boolean.

Everything here is definitional.  The .opb says what each literal stands for
and what each constraint requires; it never states a consequence of those
things, even a convenient one.  Consequences get derived in the proof, where
they can be checked.

Every constraint is labelled, so nothing anywhere needs to track constraint
numbers.  "Constraint" is doing two jobs in this solver -- the model has them
and so does the .opb -- so where both are in the room at once, the ones in here
are the PB constraints.

Most lines here are one PB constraint, but a reified one -- "this literal
means that constraint" -- is one line standing for two, and veripb lets it
carry a label for each.  ReifiedPbConstraint below writes the line and works
out the constraints, so that constraints() can hand out plain ones regardless.

There is no "* #variable= ... #constraint= ..." line at the top.  Older
pseudo-Boolean tooling wanted one and veripb 3 does not, so the file starts
with the first thing worth reading.
"""

from __future__ import annotations

from dataclasses import dataclass

from .names import neg

Term = tuple[int, str]  # (coefficient, literal), where a literal may start "~"


@dataclass(frozen=True)
class PbConstraint:
    label: str
    terms: tuple[Term, ...]
    op: str  # ">=" or "<="
    rhs: int

    def render(self) -> str:
        terms = " ".join(f"{c} {lit}" for c, lit in self.terms)
        prefix = f"@{self.label} " if self.label else ""
        return f"{prefix}{terms} {self.op} {self.rhs} ;".replace("  ", " ")

    def holds_under(self, assignment: dict[str, bool]) -> bool:
        """Whether this constraint is satisfied.  Only used by the tests, but it
        is also the quickest way to see why one you just wrote is wrong."""
        total = 0
        for coefficient, literal in self.terms:
            negated = literal.startswith("~")
            value = assignment[literal[1:] if negated else literal]
            total += coefficient * (not value if negated else value)
        return total >= self.rhs if self.op == ">=" else total <= self.rhs


@dataclass(frozen=True)
class ReifiedPbConstraint:
    """A line saying that a literal *means* a constraint.

    "x1ge3 <==> 4 x1b2 2 x1b1 1 x1b0 >= 3" is one line and two PB constraints,
    one for each direction, and it carries a label for each of them.  veripb
    works out what those two constraints are; so does expand(), so that
    everything else in here can go on seeing plain PB constraints.
    """

    labels: tuple[str, ...]  # one per constraint, in the order they are loaded
    literal: str
    arrow: str  # "==>", "<==" or "<==>"
    terms: tuple[Term, ...]
    rhs: int  # always a ">="

    def render(self) -> str:
        terms = " ".join(f"{c} {lit}" for c, lit in self.terms)
        labels = "".join(f"@{label} " for label in self.labels)
        return f"{labels}{self.literal} {self.arrow} {terms} >= {self.rhs} ;"

    def expand(self) -> list[PbConstraint]:
        """The PB constraints veripb loads this line as.

        Reifying is adding one big-M term, where M is the degree: with the
        literal set the wrong way the constraint asks for nothing at all.  The
        "<==" direction reifies the *negation* of the constraint instead, and
        negating a ">= d" over n terms is negating every literal and asking for
        (sum of the coefficients) - d + 1.
        """
        halves = []
        if self.arrow in ("==>", "<==>"):
            halves.append((list(self.terms), self.rhs, neg(self.literal)))
        if self.arrow in ("<==", "<==>"):
            halves.append((
                [(c, neg(lit)) for c, lit in self.terms],
                sum(c for c, _ in self.terms) - self.rhs + 1,
                self.literal,
            ))
        return [
            PbConstraint(label, tuple(terms + [(degree, guard)]), ">=", degree)
            for label, (terms, degree, guard) in zip(self.labels, halves)
        ]


class OpbFile:
    def __init__(self) -> None:
        self.lines: list[str | PbConstraint | ReifiedPbConstraint] = []

    def comment(self, text: str = "") -> None:
        self.lines.append(f"* {text}".rstrip())

    def constraint(
        self, label: str, terms: list[Term], op: str, rhs: int
    ) -> PbConstraint:
        if op not in (">=", "<="):
            raise ValueError(f"{op}: write two inequalities rather than an equality")
        constraint = PbConstraint(label, tuple(terms), op, rhs)
        self.lines.append(constraint)
        return constraint

    def reified(
        self, labels: list[str], literal: str, arrow: str, terms: list[Term], rhs: int
    ) -> ReifiedPbConstraint:
        if len(labels) != (2 if arrow == "<==>" else 1):
            raise ValueError(f"{arrow}: one label per constraint the line stands for")
        constraint = ReifiedPbConstraint(
            tuple(labels), literal, arrow, tuple(terms), rhs
        )
        self.lines.append(constraint)
        return constraint

    def constraints(self) -> list[PbConstraint]:
        """Every PB constraint in the file, with each reified line expanded
        into the one or two constraints veripb loads it as."""
        constraints = []
        for line in self.lines:
            if isinstance(line, PbConstraint):
                constraints.append(line)
            elif isinstance(line, ReifiedPbConstraint):
                constraints.extend(line.expand())
        return constraints

    def variables(self) -> set[str]:
        """Every PB variable mentioned anywhere -- a literal and its negation
        are one variable between them, so the "~" comes off.  Only the tests
        need this."""
        return {
            literal.lstrip("~")
            for constraint in self.constraints()
            for _, literal in constraint.terms
        }

    def render(self) -> str:
        body = [line if isinstance(line, str) else line.render() for line in self.lines]
        return "\n".join(body) + "\n"
