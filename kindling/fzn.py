"""Reading a model that MiniZinc flattened for us.

This is the only file that knows anything about FlatZinc, and nothing else
knows this file exists.  The solver's idea of a model is variables numbered
from one with domains starting at zero; turning somebody else's format into
that is a translation problem and is kept where translation problems belong.

The important rule here is to fail loudly.  A reader that quietly skips a
constraint it does not recognise produces a *checkable proof of the wrong
thing*, which is the worst outcome available to us -- the checker would agree
with a refutation of a problem nobody asked about.  So every constraint has to
be understood or the load stops.

What MiniZinc does to a model on the way through is worth knowing about:

  * A disequality against a constant disappears into the variable's domain, so
    domains arrive with holes in them.  x != 2 over 1..4 becomes [[1,1],[3,4]].
  * Tuples in a table are flattened into one long list, and the arity has to be
    recovered from how many variables there are.
  * Constants are hoisted into a separate "arrays" section and referred to by
    name, so an argument that looks like a variable may be a list of numbers.
  * Anything the solver did not declare native gets decomposed, usually into
    something with int_lin_ne in it, which kindling cannot do at all.
"""

from __future__ import annotations

import json
import pathlib

from .constraints.all_different_int import AllDifferentInt
from .constraints.int_lin_le import IntLinLe
from .constraints.table_int import TableInt
from .model import Model, Variable


class Unsupported(Exception):
    """Something in the file that kindling cannot honestly represent."""


# What we accept, and what the flattener may have called it.  Gecode's library
# names its table constraint after itself; tools/mzn2fzn.py renames it on the
# way out, and the alias is here so a hand-made file works either way.
ALIASES = {
    "all_different_int": "all_different_int",
    "fzn_all_different_int": "all_different_int",
    "table_int": "table_int",
    "fzn_table_int": "table_int",
    "gecode_table_int": "table_int",
    "int_lin_le": "int_lin_le",
    "int_lin_eq": "int_lin_eq",
}


class Reader:
    def __init__(self, document: dict) -> None:
        self.document = document
        self.arrays = {
            name: entry["a"] for name, entry in document.get("arrays", {}).items()
        }
        self.model = Model()
        self.variables: dict[str, Variable] = {}

    # --- getting at arguments ----------------------------------------------

    def values(self, argument) -> list:
        """An argument that should be a list, whether it was written out in
        full or hoisted into the arrays section and referred to by name."""
        if isinstance(argument, str):
            if argument not in self.arrays:
                raise Unsupported(f"no array called {argument}")
            return self.arrays[argument]
        if isinstance(argument, list):
            return argument
        raise Unsupported(f"expected a list, got {argument!r}")

    def integers(self, argument) -> list[int]:
        found = self.values(argument)
        if not all(isinstance(v, int) for v in found):
            raise Unsupported(f"expected a list of numbers, got {found!r}")
        return found

    def scope(self, argument) -> tuple[list[Variable], int]:
        """A list of variables, plus the constant left over from any numbers
        that were sitting among them."""
        scope, constant = [], 0
        for item in self.values(argument):
            if isinstance(item, int):
                constant += item
            elif item in self.variables:
                scope.append(self.variables[item])
            else:
                raise Unsupported(f"no variable called {item}")
        return scope, constant

    def integer(self, argument) -> int:
        if not isinstance(argument, int):
            raise Unsupported(f"expected a number, got {argument!r}")
        return argument

    # --- variables ----------------------------------------------------------

    def read_variables(self) -> None:
        for name, entry in self.document.get("variables", {}).items():
            if entry.get("type") != "int":
                raise Unsupported(
                    f"{name} is a {entry.get('type')}; kindling only has integers"
                )
            if "domain" not in entry:
                raise Unsupported(f"{name} has no domain, and kindling needs bounds")
            allowed = sorted(
                v for low, high in entry["domain"] for v in range(low, high + 1)
            )
            if allowed[0] < 0:
                raise Unsupported(
                    f"{name} can be negative, and kindling's variables start at zero"
                )
            x = self.model.add_variable(allowed[-1], name)
            self.variables[name] = x
            self.restrict(x, allowed)

    def restrict(self, x: Variable, allowed: list[int]) -> None:
        """Everything kindling makes starts at zero and has no holes, so a
        domain that does not gets the difference put back as a constraint."""
        if allowed == list(range(0, x.ub + 1)):
            return
        if allowed == list(range(allowed[0], x.ub + 1)):
            # just a lower bound: -x <= -lower
            self.model.add_constraint(IntLinLe([-1], [x], -allowed[0]))
        else:
            # holes, so say which values are allowed and let table do it
            self.model.add_constraint(TableInt([x], [(v,) for v in allowed]))

    # --- constraints --------------------------------------------------------

    def read_constraints(self) -> None:
        for entry in self.document.get("constraints", []):
            identifier = entry.get("id", "")
            known = ALIASES.get(identifier)
            if known is None:
                raise Unsupported(
                    f"kindling does not have {identifier}. It has int_lin_le, "
                    "int_lin_eq, all_different_int and table_int, and refuses to "
                    "guess at anything else."
                )
            getattr(self, f"read_{known}")(entry["args"])

    def read_int_lin_le(self, args) -> None:
        coefficients = self.integers(args[0])
        scope, constant = self.scope(args[1])
        self.model.add_constraint(
            IntLinLe(coefficients, scope, self.integer(args[2]) - constant)
        )

    def read_int_lin_eq(self, args) -> None:
        """An equality is two inequalities, and the second one is the first
        with every sign turned round."""
        coefficients = self.integers(args[0])
        scope, constant = self.scope(args[1])
        rhs = self.integer(args[2]) - constant
        self.model.add_constraint(IntLinLe(coefficients, scope, rhs))
        self.model.add_constraint(IntLinLe([-c for c in coefficients], scope, -rhs))

    def read_all_different_int(self, args) -> None:
        scope, constant = self.scope(args[0])
        if constant:
            raise Unsupported("all_different over a list containing a constant")
        self.model.add_constraint(AllDifferentInt(scope))

    def read_table_int(self, args) -> None:
        scope, constant = self.scope(args[0])
        if constant:
            raise Unsupported("table over a list containing a constant")
        flat = self.integers(args[1])
        if len(flat) % len(scope) != 0:
            raise Unsupported(
                f"table over {len(scope)} variables with {len(flat)} values in it"
            )
        tuples = [
            tuple(flat[i : i + len(scope)]) for i in range(0, len(flat), len(scope))
        ]
        self.model.add_constraint(TableInt(scope, tuples))


def read(source) -> Model:
    """A path, or the text of a .fzn.json file, or the parsed thing itself."""
    if isinstance(source, (str, pathlib.Path)) and pathlib.Path(source).exists():
        document = json.loads(pathlib.Path(source).read_text())
    elif isinstance(source, str):
        document = json.loads(source)
    else:
        document = source

    method = document.get("solve", {}).get("method", "satisfy")
    if method != "satisfy":
        raise Unsupported(f"this asks to {method}, and kindling only satisfies")

    reader = Reader(document)
    reader.read_variables()
    reader.read_constraints()
    return reader.model
