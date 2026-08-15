"""The .opb file: what the problem means, in pseudo-Boolean.

Everything here is definitional.  The .opb says what each literal stands for
and what each constraint requires; it never states a consequence of those
things, even a convenient one.  Consequences get derived in the proof, where
they can be checked.

Every constraint is labelled, so nothing anywhere needs to track constraint
numbers.  "Constraint" is doing two jobs in this solver -- the model has them
and so does the .opb -- so where both are in the room at once, the ones in here
are the PB constraints.

There is no "* #variable= ... #constraint= ..." line at the top.  Older
pseudo-Boolean tooling wanted one and veripb 3 does not, so the file starts
with the first thing worth reading.
"""

from __future__ import annotations

from dataclasses import dataclass

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


class OpbFile:
    def __init__(self) -> None:
        self.lines: list[str | PbConstraint] = []

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

    def constraints(self) -> list[PbConstraint]:
        return [line for line in self.lines if isinstance(line, PbConstraint)]

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
