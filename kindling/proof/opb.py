"""The .opb file: what the problem means, in pseudo-Boolean.

Everything here is definitional.  The .opb says what each atom stands for and
what each constraint requires; it never states a consequence of those things,
even a convenient one.  Consequences get derived in the proof, where they can
be checked.

Every row is labelled, so nothing anywhere needs to track constraint numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

Term = tuple[int, str]  # (coefficient, literal), where a literal may start "~"


@dataclass(frozen=True)
class Row:
    label: str
    terms: tuple[Term, ...]
    op: str  # ">=" or "<="
    rhs: int

    def render(self) -> str:
        terms = " ".join(f"{c} {lit}" for c, lit in self.terms)
        prefix = f"@{self.label} " if self.label else ""
        return f"{prefix}{terms} {self.op} {self.rhs} ;".replace("  ", " ")

    def holds_under(self, assignment: dict[str, bool]) -> bool:
        """Whether this row is satisfied.  Only used by the tests, but it is
        also the quickest way to see why a row you just wrote is wrong."""
        total = 0
        for coefficient, literal in self.terms:
            negated = literal.startswith("~")
            value = assignment[literal[1:] if negated else literal]
            total += coefficient * (not value if negated else value)
        return total >= self.rhs if self.op == ">=" else total <= self.rhs


class OpbFile:
    def __init__(self) -> None:
        self.lines: list[str | Row] = []

    def comment(self, text: str = "") -> None:
        self.lines.append(f"* {text}".rstrip())

    def constraint(self, label: str, terms: list[Term], op: str, rhs: int) -> Row:
        if op not in (">=", "<="):
            raise ValueError(f"{op}: write two rows rather than an equality")
        row = Row(label, tuple(terms), op, rhs)
        self.lines.append(row)
        return row

    def rows(self) -> list[Row]:
        return [line for line in self.lines if isinstance(line, Row)]

    def atoms(self) -> set[str]:
        return {
            literal.lstrip("~")
            for row in self.rows()
            for _, literal in row.terms
        }

    def render(self) -> str:
        rows = self.rows()
        header = f"* #variable= {len(self.atoms())} #constraint= {len(rows)}"
        body = [line if isinstance(line, str) else line.render() for line in self.lines]
        return "\n".join([header] + body) + "\n"
